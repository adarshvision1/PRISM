"""Four policies, one trained checkpoint, 10 temporal intervals from validation 08."""
import argparse,json,time,platform,tracemalloc
from pathlib import Path
import numpy as np
import psutil,torch
from backend.labels import ROOT,read_scan,read_truth
from backend.model.pointnet_inference import PointNetPredictor
from backend.grid_engine.ndtree import NdTree,CONFIGS
from backend.localization.odometry import motion,world_pose
from backend.application.perception_pipeline import process_frame
from .metrics import confusion,scores
BANDS=[(0,10),(10,25),(25,60),(60,100)]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=0);ap.add_argument('--demo-per-chunk',type=int,default=8);args=ap.parse_args()
    predictor=PointNetPredictor()
    if predictor.metadata['status'].startswith('untrained'):raise RuntimeError('Benchmark requires a trained checkpoint; interim is excluded')
    paths=sorted((ROOT/'data/dataset/sequences/08/velodyne').glob('*.bin'))
    if args.limit:paths=[paths[i] for i in np.linspace(0,len(paths)-1,min(args.limit,len(paths)),dtype=int)]
    sums={m:np.zeros((4,5),np.int64) for m in CONFIGS};band_sums={m:[np.zeros((4,5),np.int64) for _ in BANDS] for m in CONFIGS}
    chunk_sums={m:[[np.zeros((4,5),np.int64) for _ in BANDS] for _ in range(10)] for m in CONFIGS}
    frame_stats={m:[] for m in CONFIGS};counts=np.zeros(10,int);inference=[];rss=[];all_rows=[];grid_peak={};process=psutil.Process()
    predictor.predict(read_scan(paths[0])) # warm-up excluded from timing
    torch.cuda.reset_peak_memory_stats() if torch.cuda.is_available() else None
    for index,path in enumerate(paths):
        points=read_scan(path);truth=read_truth(path.parent.parent/'labels'/f'{path.stem}.label')
        classes,confidence,timing,_=predictor.predict(points);inference.append(timing['inference_ms'])
        radius=np.linalg.norm(points[:,:2],axis=1);chunk=min(9,int(path.stem)*10//4071);counts[chunk]+=1;speed,heading=motion('08',int(path.stem));row={'frame':int(path.stem),'chunk':chunk,'inference_ms':timing['inference_ms']}
        for mode in CONFIGS:
            result=NdTree(mode).build(points,classes,confidence,speed=speed,heading=heading)
            matrix=confusion(truth,result.point_classes,radius<100);sums[mode]+=matrix
            bands=[]
            for j,(lo,hi) in enumerate(BANDS):
                cm=confusion(truth,result.point_classes,(radius>=lo)&(radius<hi));band_sums[mode][j]+=cm;chunk_sums[mode][chunk][j]+=cm;bands.append(scores(cm)['miou'])
            detail={'cells':len(result.nodes),'bytes':result.nodes.nbytes,'grid_ms':result.elapsed_ms,'pipeline_ms':timing['inference_ms']+result.elapsed_ms,'bands':bands,**scores(matrix)};frame_stats[mode].append(detail);row[mode]=detail
        if index==0:
            for mode in CONFIGS:
                tracemalloc.start();measured=NdTree(mode).build(points,classes,confidence,speed=speed,heading=heading);_,peak=tracemalloc.get_traced_memory();tracemalloc.stop();grid_peak[mode]=peak/1048576
        all_rows.append(row);rss.append(process.memory_info().rss/1048576)
        if index%20==0:print('Evaluation',index+1,'/',len(paths),flush=True)
    modes={}
    for mode in CONFIGS:
        stats=frame_stats[mode];out={k:float(np.mean([s[k] for s in stats])) for k in ['cells','bytes','grid_ms','pipeline_ms']}
        out.update(scores(sums[mode]));out['pipeline_fps']=1000/out['pipeline_ms'];out['grid_fps']=1000/out['grid_ms'];out['confusion']=sums[mode].tolist();out['peak_grid_allocation_mb_first_frame']=grid_peak[mode]
        out['bands']=[]
        for j in range(4):
            band=scores(band_sums[mode][j]);values=[s['bands'][j] for s in stats if s['bands'][j] is not None];band['spread']=float(np.std(values)) if values else None;out['bands'].append(band)
        modes[mode]=out
    chunks=[]
    for i in range(10):
        delta=[]
        for j in range(4):
            a=scores(chunk_sums['uniform'][i][j])['miou'];b=scores(chunk_sums['prism'][i][j])['miou'];delta.append(b-a if a is not None and b is not None else None)
        chunks.append({'start':int(np.ceil(i*4071/10)),'end':int(np.ceil((i+1)*4071/10))-1,'frames':int(counts[i]),'delta':delta})
    # Actual allocated dense uint8 occupancy volume and sparse occupied xyz keys,
    # same 20x20x4m domain. No invented theoretical allocation called measurement.
    points=read_scan(paths[0]);local=(np.abs(points[:,0])<10)&(np.abs(points[:,1])<10)&(points[:,2]>=-3)&(points[:,2]<1)
    dense=np.zeros((400,400,80),np.uint8);coords=np.floor((points[local,:3]-[-10,-10,-3])/.05).astype(np.int32)
    keys=np.unique((coords[:,0].astype(np.int64)*400+coords[:,1])*80+coords[:,2]);dense.reshape(-1)[keys]=1
    classes,confidence,_,_=predictor.predict(points);grid=NdTree('prism').build(points[local],classes[local],confidence[local])
    report={'frames':len(paths),'coverage':f'{len(paths)} available scans of 4,071 sequence-08 frames; 10 fixed contiguous temporal intervals, sampled coverage (not full-sequence evaluation).','model':predictor.metadata,'hardware':{'device':torch.cuda.get_device_name(0) if torch.cuda.is_available() else platform.processor(),'torch':torch.__version__,'platform':platform.platform()},'inference_ms':float(np.mean(inference)),'peak_rss_mb':max(rss),'peak_gpu_mb':torch.cuda.max_memory_allocated()/1048576 if torch.cuda.is_available() else 0,'modes':modes,'chunks':chunks,'voxel':{'domain_m':[20,20,4],'resolution_m':.05,'dense_uint8_bytes':dense.nbytes,'sparse_int64_key_bytes':keys.nbytes,'local_prism_leaf_bytes':grid.nodes.nbytes},'voxel_note':f'First evaluated scan, identical 20 × 20 × 4 m domain: allocated dense 5 cm uint8 3D occupancy = {dense.nbytes:,} bytes; sparse occupied 3D int64 keys = {keys.nbytes:,} bytes; PRISM 2.5D leaves = {grid.nodes.nbytes:,} bytes. These representations carry different attributes. PRISM is not claimed to beat sparse 3D keys.','per_frame':all_rows}
    (ROOT/'data/pointnet_benchmark.json').write_text(json.dumps(report,indent=2));print('Metrics saved',flush=True)
    folder=ROOT/'data/pointnet_frames';folder.mkdir(exist_ok=True);demo={'chunks':[],'model':predictor.metadata};counter=0
    for i in range(10):
        choices=[p for p in paths if min(9,int(p.stem)*10//4071)==i];selected=[]
        # Prefer an actual contiguous clip, never animate across a missing-data gap.
        for p in choices:
            if selected and int(p.stem)!=int(selected[-1].stem)+1:break
            selected.append(p)
            if len(selected)>=args.demo_per_chunk:break
        indices=[];previous=None
        for p in selected:
            frame_id=int(p.stem);source={'points':read_scan(p),'pose':world_pose('08',frame_id),'timestamp':frame_id*.1,'name':f'08/{p.stem}','domain':'SemanticKITTI validation 08'}
            result,previous=process_frame(predictor,source,previous);result['index']=counter
            (folder/f'{counter:05d}.json').write_text(json.dumps(result,separators=(',',':')));indices.append(counter);counter+=1
        demo['chunks'].append({'chunk':i,'indices':indices,'frame_ids':[int(p.stem) for p in selected]});print('Demo chunk',i+1,flush=True)
    (ROOT/'data/pointnet_demo.json').write_text(json.dumps(demo,indent=2))
if __name__=='__main__':main()
