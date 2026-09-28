"""Attach real GT, voxel geometry and uncertainty to cached demo frames."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from backend.labels import read_scan,read_truth
from backend.model.pointnet_inference import PointNetPredictor
from backend.grid_engine.ndtree import NdTree
from backend.application.scene_service import voxel_reference
def main():
    p=PointNetPredictor();demo=json.loads((ROOT/'data/pointnet_demo.json').read_text())
    for chunk in demo['chunks']:
        for i,stem in zip(chunk['indices'],chunk['frame_ids']):
            path=ROOT/'data/pointnet_frames'/f'{i:05d}.json';f=json.loads(path.read_text())
            points=read_scan(ROOT/'data/dataset/sequences/08/velodyne'/f'{stem:06d}.bin');truth=read_truth(ROOT/'data/dataset/sequences/08/labels'/f'{stem:06d}.label')
            classes,confidence,_,_=p.predict(points)
            idx=np.linspace(0,len(points)-1,min(14000,len(points)),dtype=int)
            f['points']=np.c_[points[idx,:3],classes[idx],confidence[idx],truth[idx]].round(4).tolist()
            f['voxel']=voxel_reference(points)
            for mode in ('uniform','prism'):
                g=NdTree(mode).build(points,classes,confidence,speed=f['speed_mps'],heading=f['heading']);n=g.nodes
                valid=(truth<4)&(g.point_cells>=0)
                v=np.bincount(g.point_cells[valid]*4+truth[valid],minlength=len(n)*4).reshape(-1,4);gt=v.argmax(1);gt[v.sum(1)==0]=255
                show=np.linspace(0,len(n)-1,min(16000,len(n)),dtype=int)
                cells=np.column_stack([n[k][show] for k in ('x','y','size','dominant_class','mean_z','class_confidence','min_z','max_z','height_variance')]+[gt[show]])
                f['grids'][mode]={'cells':cells.round(4).tolist(),'active_cells':len(n),'bytes':n.nbytes,'grid_ms':g.elapsed_ms,'render_cap':16000}
            path.write_text(json.dumps(f,separators=(',',':')))
        print('Enriched interval',chunk['chunk']+1,flush=True)
    demo['model']=p.metadata
    (ROOT/'data/pointnet_demo.json').write_text(json.dumps(demo,indent=2))
if __name__=='__main__':main()
