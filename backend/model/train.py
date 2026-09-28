"""Time-boxed AMP training; atomic best-validation checkpoint selection."""
from pathlib import Path
import argparse,csv,json,time,os,random,signal,gc
import numpy as np
import torch
from torch.utils.data import Dataset,DataLoader
from .registry import build_model, get_spec, MODELS, checkpoint_architecture
from .training_lock import training_lock
from .losses import ace_lovasz
ROOT=Path(__file__).resolve().parents[2]
class BlockDataset(Dataset):
    def __init__(self,split,augment=False,cache_dir=None):
        self.root=Path(cache_dir) if cache_dir else ROOT/'data/blocks_cache'
        if not self.root.is_absolute(): self.root=ROOT/self.root
        self.meta=json.loads((self.root/'manifest.json').read_text())[split]
        self.x=np.load(self.root/f'{split}_x.npy',mmap_mode='r'); self.y=np.load(self.root/f'{split}_y.npy',mmap_mode='r'); self.augment=augment
    def __len__(self):return self.meta['blocks']
    def __getitem__(self,i):
        x=self.x[i].copy(); y=self.y[i].astype(np.int64)
        if self.augment:
            # Local block-centered rotation preserves metric radii and height.
            angle=np.random.uniform(-np.pi,np.pi); co,si=np.cos(angle),np.sin(angle)
            x[:,:2]=(x[:,:2]-5)@np.array([[co,-si],[si,co]],np.float32)+5
            order=np.random.permutation(len(x)); x=x[order]; y=y[order]
        return torch.from_numpy(x.T.copy()),torch.from_numpy(y)
def save_checkpoint(path,model,**meta):
    path.parent.mkdir(exist_ok=True,parents=True); tmp=path.with_suffix('.tmp')
    torch.save({'state_dict':model.state_dict(),'model_config':model.config,'architecture':getattr(model,'architecture','pointnet2'),**meta},tmp); os.replace(tmp,path)
def score(conf):
    union=conf.sum(0)+conf.sum(1)-conf.diagonal(); valid=union>0
    return float(np.mean(conf.diagonal()[valid]/union[valid])) if valid.any() else 0.

def next_epoch_index(checkpoint_epoch, history):
    """Choose the next unique log/checkpoint ID when resuming best weights."""
    last_logged=max((int(row['epoch']) for row in history),default=0)
    return max(int(checkpoint_epoch),last_logged)
def validate(model,loader,device):
    model.eval(); conf=np.zeros((4,4),np.int64)
    with torch.inference_mode():
        for x,y in loader:
            with torch.autocast(device_type=device.type,enabled=device.type=='cuda'):
                pred=model(x.to(device,non_blocking=device.type=='cuda')).argmax(1).cpu().numpy()
            target=y.numpy(); valid=target<4
            conf+=np.bincount(target[valid]*4+pred[valid],minlength=16).reshape(4,4)
    return score(conf),conf
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--epochs',type=int,default=12); ap.add_argument('--minutes',type=float,default=30); ap.add_argument('--patience',type=int,default=4); ap.add_argument('--radius-scale',type=float,default=1.); ap.add_argument('--init-only',action='store_true');ap.add_argument('--resume',action='store_true');ap.add_argument('--lr',type=float,default=.001); ap.add_argument('--cache-dir',default='data/blocks_cache_expanded',help='Prepared train/validation block cache directory'); ap.add_argument('--architecture',choices=MODELS,default='pointnet2'); args=ap.parse_args()
    if args.minutes<=0 or args.epochs<1 or args.lr<=0:ap.error('Time, epochs and learning rate must be positive')
    spec=get_spec(args.architecture)
    torch.manual_seed(53); np.random.seed(53); random.seed(53); torch.set_num_threads(4)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); model=build_model(args.architecture,radius_scale=args.radius_scale).to(device)
    weights=spec.weights; interim=weights/'interim.ckpt'
    if spec.checkpoint.exists() and not args.resume and not args.init_only:
        raise ValueError('Best weights already exist. Use --resume to preserve the trained model and its validation history.')
    previous_checkpoint=None
    if args.resume:
        previous_checkpoint=torch.load(spec.checkpoint,map_location='cpu',weights_only=True)
        if checkpoint_architecture(previous_checkpoint)!=args.architecture:raise ValueError('Wrong architecture in resume checkpoint')
        model=build_model(args.architecture,**previous_checkpoint['model_config']).to(device);model.load_state_dict(previous_checkpoint['state_dict'])
    if not interim.exists(): save_checkpoint(interim,model,status='untrained interim',epoch=0,val_miou=None)
    if args.init_only: print('Interim checkpoint ready'); return
    train=BlockDataset('train',True,args.cache_dir); valid=BlockDataset('valid',cache_dir=args.cache_dir); start=time.monotonic(); deadline=start+args.minutes*60
    # Keep time for final validation/checkpoint bookkeeping inside the user's
    # requested wall-clock cap instead of beginning an epoch-sized overrun.
    validation_reserve=min(45.,max(1.,args.minutes*60*.05)); train_deadline=deadline-validation_reserve
    if not len(train) or not len(valid): raise ValueError('Training and validation blocks required')
    opt=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=.0001)
    scaler=torch.amp.GradScaler('cuda',enabled=device.type=='cuda'); batch=16
    probe_state={key:value.detach().cpu().clone() for key,value in model.state_dict().items()}
    while batch>=1:
        try:
            samples=[train[i%len(train)] for i in range(batch)]
            x=torch.stack([s[0] for s in samples]).to(device); y=torch.stack([s[1] for s in samples]).to(device)
            with torch.autocast(device_type=device.type,enabled=device.type=='cuda'): loss=ace_lovasz(model(x),y)
            scaler.scale(loss).backward(); opt.zero_grad(set_to_none=True); del x,y,loss; break
        except torch.cuda.OutOfMemoryError:
            opt.zero_grad(set_to_none=True);x=y=loss=None;gc.collect();batch//=2;torch.cuda.empty_cache()
    if batch<1: raise RuntimeError('Even one 4096-point block exceeds available VRAM')
    model.load_state_dict(probe_state);del probe_state
    print('Device',device,'stable batch',batch,flush=True)
    # Pinned host batches reduce synchronous H2D copies on CUDA without adding
    # Windows multiprocessing workers or changing the point sampling path.
    loader=DataLoader(train,batch_size=batch,shuffle=True,num_workers=0,pin_memory=device.type=='cuda'); val_loader=DataLoader(valid,batch_size=batch,num_workers=0,pin_memory=device.type=='cuda')
    best=-1.; best_epoch=0; bad=0; log=spec.log; history=[];start_epoch=0;history_start_len=0
    log.parent.mkdir(parents=True,exist_ok=True);spec.run.parent.mkdir(parents=True,exist_ok=True)
    if previous_checkpoint:
        model.eval();baseline,_=validate(model,val_loader,device)
        best=max(float(previous_checkpoint['val_miou']),baseline)
        best_epoch=int(previous_checkpoint['epoch'])
        history=list(csv.DictReader(log.open())) if log.exists() else []
        history_start_len=len(history)
        # Resuming begins from the best checkpoint, which may be several
        # epochs behind the last logged epoch. Keep the display/log epoch IDs
        # monotonic while recording the actual source checkpoint separately.
        start_epoch=next_epoch_index(previous_checkpoint['epoch'],history)
    run={'device':str(device),'gpu':torch.cuda.get_device_name(0) if device.type=='cuda' else None,'stable_batch_size':batch,'amp':device.type=='cuda','max_minutes':args.minutes,'validation_reserve_seconds':validation_reserve,'max_epochs':args.epochs,'train_blocks':len(train),'validation_blocks':len(valid),'cache_dir':str(train.root.relative_to(ROOT)) if train.root.is_relative_to(ROOT) else str(train.root),'sampling':'random-centroid + radius-limited kNN; no compiled FPS','model_config':model.config,'status':'running'}
    run['architecture']=args.architecture
    run.update(
        resumed_from_epoch=(int(previous_checkpoint['epoch']) if previous_checkpoint else 0),
        log_epoch_start=start_epoch + 1,
        learning_rate=args.lr,
        initial_validation_miou=best if previous_checkpoint else None,
    )
    spec.run.write_text(json.dumps(run,indent=2))
    with log.open('a' if previous_checkpoint else 'w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['epoch','train_loss','val_miou','elapsed_seconds','steps','complete_epoch'])
        if not previous_checkpoint:writer.writeheader()
        f.flush()
        stop_requested=False
        def request_graceful_stop(signum,frame):
            nonlocal stop_requested
            stop_requested=True
        previous_sigint=signal.signal(signal.SIGINT,request_graceful_stop)
        for epoch in range(start_epoch+1,start_epoch+args.epochs+1):
            model.train(); losses=[]; complete=True
            for x,y in loader:
                if stop_requested or time.monotonic()>train_deadline: complete=False; break
                opt.zero_grad(set_to_none=True)
                with torch.autocast(device_type=device.type,enabled=device.type=='cuda'): loss=ace_lovasz(model(x.to(device,non_blocking=device.type=='cuda')),y.to(device,non_blocking=device.type=='cuda'))
                if not torch.isfinite(loss): raise FloatingPointError('Non-finite training loss')
                scaler.scale(loss).backward(); scaler.unscale_(opt); torch.nn.utils.clip_grad_norm_(model.parameters(),5)
                scaler.step(opt); scaler.update(); losses.append(float(loss.detach()))
            if not losses: break
            # Validation/checkpointing finishes the current boundary even at time-box.
            miou,conf=validate(model,val_loader,device); elapsed=time.monotonic()-start
            row={'epoch':epoch,'train_loss':float(np.mean(losses)),'val_miou':miou,'elapsed_seconds':elapsed,'steps':len(losses),'complete_epoch':complete};writer.writerow(row);f.flush();history.append(row)
            meta={'status':'trained time-boxed','epoch':epoch,'val_miou':miou,'train_blocks':len(train),'validation_blocks':len(valid),'validation_confusion':conf.tolist(),'complete_epoch':complete}
            save_checkpoint(weights/f'epoch-{epoch:03d}.ckpt',model,**meta)
            if miou>best:
                best=miou;best_epoch=epoch;bad=0;save_checkpoint(weights/'best.ckpt',model,**meta)
            else: bad+=1
            print(json.dumps(row),flush=True)
            if stop_requested or not complete or bad>=args.patience or time.monotonic()>=deadline: break
        signal.signal(signal.SIGINT,previous_sigint)
    run.update(status='interrupted' if stop_requested else 'complete',best_val_miou=best,best_epoch=best_epoch,elapsed_seconds=time.monotonic()-start,
                epochs_completed=len(history)-history_start_len,total_epochs_logged=len(history),history=history)
    spec.run.write_text(json.dumps(run,indent=2))
    if stop_requested: print(f'Graceful stop: completed validation/checkpoint boundary; best epoch {best_epoch} remains selected.',flush=True)
if __name__=='__main__':
    with training_lock():main()
