"""Accuracy-constrained inference experiments; never assumes reduced input is free."""
from pathlib import Path
import sys,json,time,gc
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.model.pointnet_inference import PointNetPredictor
from backend.labels import read_scan,read_truth
from backend.eval.metrics import confusion,scores
from backend.grid_engine.ndtree import NdTree
import torch

def select_profiles(report):
    """Keep near-field class recall within one point of the full-input run."""
    profiles=report['profiles'];ref=profiles['reference'];eligible=[]
    for name,result in profiles.items():
        result['miou_delta']=result['miou']-ref['miou']
        recalls=np.asarray(result['near']['recall'],dtype=float)
        reference_recalls=np.asarray(ref['near']['recall'],dtype=float)
        result['eligible']=bool(result['miou_delta']>=-.01 and np.all(recalls>=reference_recalls-.01))
        if result['eligible']:eligible.append(name)
    if not eligible:raise RuntimeError('No runtime profile meets the mIoU and near-field recall constraints')
    report['recommended']=max(eligible,key=lambda n:profiles[n]['fps'])
    report['selection_rule']='Fastest measured profile with at most 1.0 percentage point overall mIoU loss and no more than 1.0 point recall loss for any class in 0 to 10 m, compared with 4096-point full-input batch-8 reference. This explicitly protects near-field class recall; exploratory sequence-08 validation, not an independent test.'
    return report

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--frames',type=int,default=32);args=ap.parse_args()
    folder=ROOT/'data/performance_trials';folder.mkdir(exist_ok=True)
    cfg=json.loads((ROOT/'config.json').read_text())
    profiles={'reference':{'inference_batch_size':8,'input_points_per_block':4096,'far_points_per_block':None},
              'batch16':{'inference_batch_size':16,'input_points_per_block':4096,'far_points_per_block':None},
              'foveated1024':{'inference_batch_size':16,'input_points_per_block':4096,'far_points_per_block':1024},
              'compact2048':{'inference_batch_size':16,'input_points_per_block':2048,'far_points_per_block':1024}}
    paths=sorted((ROOT/'data/dataset/sequences/08/velodyne').glob('*.bin'))
    paths=[paths[i] for i in np.linspace(0,len(paths)-1,args.frames,dtype=int)];report={'frames':[int(p.stem) for p in paths],'scope':'inference + PRISM grid; detection/I/O/render excluded','profiles':{}}
    for name,params in profiles.items():
        p=folder/f'{name}.json';p.write_text(json.dumps({**cfg,**params}));model=PointNetPredictor(p)
        model.predict(read_scan(paths[0]));rows=[];cm=np.zeros((4,5),np.int64);near=cm.copy()
        for path in paths:
            cloud=read_scan(path);truth=read_truth(path.parent.parent/'labels'/f'{path.stem}.label');radius=np.linalg.norm(cloud[:,:2],axis=1)
            c,q,t,_=model.predict(cloud);g=NdTree().build(cloud,c,q)
            cm+=confusion(truth,g.point_classes,radius<100);near+=confusion(truth,g.point_classes,radius<10)
            rows.append({**{k:t[k] for k in ['preprocess_ms','network_ms','reassemble_ms','inference_ms','network_points']},'grid_ms':g.elapsed_ms,'pipeline_ms':t['inference_ms']+g.elapsed_ms})
        result={'config':params,**scores(cm),'near':scores(near),'mean':{k:float(np.mean([r[k] for r in rows])) for k in rows[0]},'per_frame':rows,'checkpoint':model.metadata['sha256']};result['fps']=1000/result['mean']['pipeline_ms'];report['profiles'][name]=result
        print(name,'miou',result['miou'],'fps',result['fps'],'network points',result['mean']['network_points'],flush=True)
        (ROOT/'data/performance_trials.json').write_text(json.dumps(report,indent=2));del model;gc.collect();torch.cuda.empty_cache()
    select_profiles(report)
    (ROOT/'data/performance_trials.json').write_text(json.dumps(report,indent=2));print('Recommended',report['recommended'],flush=True)
if __name__=='__main__':main()
