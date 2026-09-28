"""Interactive grid experiments use full clouds; display decimation never feeds metrics."""
import json, threading, time
from collections import OrderedDict
import numpy as np
from backend.labels import ROOT, read_scan, read_truth
from backend.grid_engine.ndtree import NdTree

_cache = OrderedDict()
_lock = threading.RLock()
_last_grids = OrderedDict()

def encode_grid(g,truth=None):
    n = g.nodes
    view = n[np.linspace(0, len(n)-1, min(len(n), 16000), dtype=int)] if len(n) else n
    columns=[view[k] for k in ('x','y','size','dominant_class','mean_z','class_confidence','min_z','max_z','height_variance')]
    if truth is not None:
        valid=(truth<4)&(g.point_cells>=0)
        votes=np.bincount(g.point_cells[valid]*4+truth[valid],minlength=len(n)*4).reshape(-1,4)
        gt=votes.argmax(1);gt[votes.sum(1)==0]=255
        columns.append(gt[np.linspace(0,len(n)-1,min(len(n),16000),dtype=int)] if len(n) else gt)
    cells = np.column_stack(columns)
    return dict(cells=cells.round(4).tolist(), active_cells=len(n), bytes=n.nbytes, grid_ms=g.elapsed_ms, render_cap=16000)

def voxel_reference(points):
    start=time.perf_counter()
    mask=(points[:,0]>=-10)&(points[:,0]<10)&(points[:,1]>=-10)&(points[:,1]<10)&(points[:,2]>=-3)&(points[:,2]<1)
    xyz=points[mask,:3]
    coord=np.floor((xyz-[-10,-10,-3])/.05).astype(np.int32)
    dense=np.zeros((400,400,80),np.uint8)
    if len(coord): dense[coord[:,0],coord[:,1],coord[:,2]]=1
    elapsed=(time.perf_counter()-start)*1000
    unique=np.argwhere(dense)
    sample=unique[np.linspace(0,len(unique)-1,min(len(unique),8000),dtype=int)] if len(unique) else unique
    return dict(bytes=dense.nbytes, grid_ms=elapsed, occupied=len(unique), point_count=len(xyz),
                cells=(sample*.05+[-10,-10,-3]).round(3).tolist(), resolution=.05,
                domain='20 × 20 × 4 m local crop', bounds=[-10,10,-10,10,-3,1], render_cap=8000)

def fusion(manager, demo_index, speed_kmh, job_id=None, frame_index=0, heading=0.0):
    """Bounded prediction cache; speed sweeps rerun only the actual grid engine."""
    with _lock:
        cfg=json.loads((ROOT/'config.json').read_text())
        checkpoint=ROOT/cfg['checkpoint']
        key=(job_id,frame_index) if job_id else ('demo',demo_index,checkpoint.stat().st_mtime_ns,(ROOT/'config.json').stat().st_mtime_ns)
        if key not in _cache:
            if job_id:
                path=ROOT/'data/jobs'/job_id/f'source-{frame_index:05d}.npz'
                if not path.exists(): raise ValueError('This older result has no full-cloud cache. Run the sequence again.')
                with np.load(path) as z: points=z['points'];classes=z['classes'];confidence=z['confidence']
                metadata=None
            else:
                frame_path=ROOT/'data/pointnet_frames'/f'{demo_index:05d}.json'
                if not frame_path.exists():raise ValueError('Unknown demo frame')
                f=json.loads(frame_path.read_text()); name=f['name'].replace('\\','/')
                # Demo names are 08/000000; only manifest-backed numeric frame IDs allowed.
                stem=name.split('/')[-1].split('.')[0]
                if not stem.isdigit():raise ValueError('Invalid source frame identifier')
                points=read_scan(ROOT/'data/dataset/sequences/08/velodyne'/f'{int(stem):06d}.bin')
                with manager.lock:
                    # Demo regrids must not use or replace an upload's selected model.
                    from backend.model.inference import SegmentationPredictor
                    demo_predictor=SegmentationPredictor(architecture='pointnet2',freeze=True)
                    classes,confidence,timing,_=demo_predictor.predict(points)
                    metadata=timing['model']
                    del demo_predictor
            _cache[key]=(points,classes,confidence,metadata)
            while len(_cache)>4:_cache.popitem(last=False)
        _cache.move_to_end(key)
        points,classes,confidence,metadata=_cache[key]
        truth=None
        if not job_id:
            f=json.loads((ROOT/'data/pointnet_frames'/f'{demo_index:05d}.json').read_text())
            stem=f['name'].replace('\\','/').split('/')[-1].split('.')[0]
            gtpath=ROOT/'data/dataset/sequences/08/labels'/f'{int(stem):06d}.label'
            if gtpath.exists():truth=read_truth(gtpath)
        start=time.perf_counter()
        prism=NdTree('prism').build(points,classes,confidence,speed=speed_kmh/3.6,heading=heading)
        uniform=NdTree('uniform').build(points,classes,confidence)
        voxel=voxel_reference(points)
        crop=(points[:,0]>=-10)&(points[:,0]<10)&(points[:,1]>=-10)&(points[:,1]<10)&(points[:,2]>=-3)&(points[:,2]<1)
        local=NdTree('prism').build(points[crop],classes[crop],confidence[crop],speed=speed_kmh/3.6,heading=heading)
        geometry=set(zip(prism.nodes['x'].tolist(),prism.nodes['y'].tolist(),prism.nodes['size'].tolist()))
        previous=_last_grids.get(key);changed=len(geometry.symmetric_difference(previous)) if previous is not None else None
        _last_grids[key]=geometry
        while len(_last_grids)>4:_last_grids.popitem(last=False)
        return dict(prism=encode_grid(prism,truth),uniform=encode_grid(uniform,truth),local=encode_grid(local,truth[crop] if truth is not None else None),voxel=voxel,changed_cells=changed,
                    input_points=len(points),speed_kmh=speed_kmh,heading=heading,model=metadata,
                    total_ms=(time.perf_counter()-start)*1000,scope='Grid rebuild only; segmentation cached')
