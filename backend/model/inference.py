from pathlib import Path
import json,hashlib,time,io
import numpy as np
import torch
from scipy.spatial import cKDTree
from .registry import build_model, get_spec, checkpoint_architecture
from .preprocess import features,blocks
ROOT=Path(__file__).resolve().parents[2]
class SegmentationPredictor:
    def __init__(self,config_path=None,architecture='pointnet2',freeze=False):
        self.architecture=architecture;self.spec=get_spec(architecture);self.freeze=freeze
        self.config_path=Path(config_path or ROOT/'config.json');self.signature=None;self.model=None
        self.reload()
    def reload(self):
        if self.freeze and self.model is not None:return
        config=json.loads(self.config_path.read_text());path=ROOT/config['checkpoint']
        if self.architecture!='pointnet2':path=self.spec.checkpoint
        if not path.exists():raise FileNotFoundError(f'{self.spec.title} needs training before inference. No best checkpoint exists.')
        signature=(str(path),path.stat().st_mtime_ns,self.config_path.stat().st_mtime_ns)
        if signature==self.signature:return
        checkpoint_bytes=path.read_bytes()
        checkpoint=torch.load(io.BytesIO(checkpoint_bytes),map_location='cpu',weights_only=True)
        if checkpoint_architecture(checkpoint)!=self.architecture:raise ValueError('Checkpoint architecture does not match the selected model')
        if not checkpoint.get('status','').startswith('trained'):raise ValueError('An untrained checkpoint cannot be used as a trained model')
        requested=config.get('device','auto');device='cuda' if requested=='auto' and torch.cuda.is_available() else ('cpu' if requested=='auto' else requested)
        self.device=torch.device(device);self.model=build_model(self.architecture,**checkpoint['model_config']).to(self.device)
        self.model.load_state_dict(checkpoint['state_dict']);self.model.eval();self.signature=signature
        self.batch=config.get('inference_batch_size',8);self.input_n=config.get('input_points_per_block',4096);self.far_n=config.get('far_points_per_block');torch.set_num_threads(4)
        self.metadata={k:v for k,v in checkpoint.items() if k!='state_dict'}
        self.metadata.update(architecture=self.architecture,checkpoint=str(path.relative_to(ROOT)),sha256=hashlib.sha256(checkpoint_bytes).hexdigest(),device=device)
        self.metadata['runtime']={'batch_size':self.batch,'near_block_points':self.input_n,'far_block_points':self.far_n,'far_block_min_distance_m':25}
    def predict(self,points,previous=None,pose=None,previous_pose=None,progress=None):
        self.reload();start=time.perf_counter()
        if progress:progress('preprocess')
        temporal=self.metadata.get('motion_trained',False)
        feat,meta=features(points,previous if temporal else None,pose if temporal else None,previous_pose if temporal else None)
        meta['pose_available']=pose is not None
        # Current training has no adjacent pose pairs. Do not feed unseen residuals
        # to its trained sixth channel; expose geometric residual separately.
        if not self.metadata.get('motion_trained',False):feat[:,5]=0
        packed=list(blocks(feat,n=self.input_n,far_n=self.far_n));prep_ms=(time.perf_counter()-start)*1000
        # Bucket equal-length tensors; preserve each block's original indices.
        packed.sort(key=lambda b:len(b['features']))
        probabilities=np.zeros((len(points),4),np.float32);net_ms=0.;restore_ms=0.
        with torch.inference_mode():
            batches=[]
            for length in sorted({len(b['features']) for b in packed}):
                group=[b for b in packed if len(b['features'])==length]
                batches.extend(group[i:i+self.batch] for i in range(0,len(group),self.batch))
            for batch in batches:
                if progress:progress('network')
                x=torch.from_numpy(np.stack([b['features'].T for b in batch])).to(self.device)
                if self.device.type=='cuda':torch.cuda.synchronize()
                tick=time.perf_counter()
                with torch.autocast(device_type=self.device.type,enabled=self.device.type=='cuda'):
                    pred=self.model(x).float().softmax(1).transpose(1,2).cpu().numpy()
                if self.device.type=='cuda':torch.cuda.synchronize()
                net_ms+=(time.perf_counter()-tick)*1000;tick=time.perf_counter()
                if progress:progress('reassembly')
                for b,probs in zip(batch,pred):
                    ids=b['indices'];sample_xyz=feat[b['sample_indices'],:3]
                    nearest=cKDTree(sample_xyz).query(points[ids,:3],workers=1)[1]
                    probabilities[ids]=probs[nearest]
                restore_ms+=(time.perf_counter()-tick)*1000
        classes=probabilities.argmax(1).astype(np.uint8);confidence=probabilities.max(1);classes[confidence==0]=255
        return classes,confidence,{'preprocess_ms':prep_ms,'network_ms':net_ms,'reassemble_ms':restore_ms,'inference_ms':(time.perf_counter()-start)*1000,'blocks':len(packed),'network_points':sum(len(b['features']) for b in packed),'input_points':len(points),'model':self.metadata,**meta},feat
