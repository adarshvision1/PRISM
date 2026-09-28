"""Derive dashboard summaries and a readable report from actual per-frame evidence."""
import sys,json,time,hashlib
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from backend.labels import read_scan,read_truth,config
from scipy.spatial import cKDTree
from backend.grid_engine.ndtree import NdTree
from backend.eval.metrics import scores
from backend.eval.grid_quality import distribution

def main():
    path=ROOT/'data/grid_evidence.json';r=json.loads(path.read_text());rows=r['per_frame']
    r['coverage']={'evaluated_validation_frames':len(rows),'total_validation_frames':4071,'available_validation_scans':len(list((ROOT/'data/dataset/sequences/08/velodyne').glob('*.bin'))),'frame_ids':[v['frame'] for v in rows],'selection':'Frozen evenly spaced selection from paired files available when run began; later downloads are not silently included.'}
    chunks=[]
    for chunk in range(10):
        selected=[v for v in rows if min(9,v['frame']*10//4071)==chunk];deltas=[]
        for j in range(4):
            vals={m:scores(sum((np.asarray(v['modes'][m]['bands'][j]['common_5cm_cell']['confusion']) for v in selected),np.zeros((4,5),int)))['miou'] for m in ('uniform','prism')}
            deltas.append(vals['prism']-vals['uniform'] if all(v is not None for v in vals.values()) else None)
        chunks.append({'frames':len(selected),'delta':deltas})
    r['chunks']=chunks
    temporal_rows=[v['temporal'] for v in rows if v.get('temporal')]
    r['temporal_summary']={k:distribution([v[k] for v in temporal_rows if v[k] is not None]) for k in ('overlap_fraction','semantic_flicker_rate','resolution_change_rate','height_stability_mae_m')}
    turns=[];sig=hashlib.sha256((r['model']['sha256']+json.dumps(r['model']['runtime'],sort_keys=True)).encode()).hexdigest()[:16]
    for index in np.linspace(0,len(rows)-1,min(16,len(rows)),dtype=int):
        frame=rows[index]['frame'];points=read_scan(ROOT/'data/dataset/sequences/08/velodyne'/f'{frame:06d}.bin')
        with np.load(ROOT/'data/evaluation_cache'/f'08-{frame:06d}-{sig}.npz') as z:cls=z['classes'];conf=z['confidence']
        previous=None
        for angle in (0,18,-18,90):
            start=time.perf_counter();g=NdTree('prism').build(points,cls,conf,speed=60/3.6,heading=np.deg2rad(angle));elapsed=(time.perf_counter()-start)*1000
            keys=set(zip(g.nodes['x'].tolist(),g.nodes['y'].tolist(),g.nodes['size'].tolist()))
            if previous is not None:turns.append({'frame':frame,'heading_degrees':angle,'grid_ms':elapsed,'changed_leaves':len(previous.symmetric_difference(keys))})
            previous=keys
    r['turn_response']={'scope':'16 validation frames; speed fixed 60km/h; headings 0, +18, -18, +90 degrees; cached segmentation; CPU grid rebuild only, not browser/network latency. Changed leaves count symmetric difference of spatial origin+size sets.','grid_ms':distribution([v['grid_ms'] for v in turns]),'changed_leaves':distribution([v['changed_leaves'] for v in turns]),'rows':turns}
    for f in r['failure_gallery']:
        if f['name']=='far pedestrian':f['name']='far pedestrian / rider'
        if f['name']=='curb / sidewalk boundary':
            frame=f['frame'];base=ROOT/'data/dataset/sequences/08'
            points=read_scan(base/'velodyne'/f'{frame:06d}.bin');truth=read_truth(base/'labels'/f'{frame:06d}.label')
            raw=np.fromfile(base/'labels'/f'{frame:06d}.label',dtype='<u4')&65535;names=config()['labels']
            road=np.isin(raw,[k for k,v in names.items() if v=='road']);side=np.isin(raw,[k for k,v in names.items() if v=='sidewalk'])
            candidates=np.flatnonzero(side)
            if road.any() and len(candidates):
                near=cKDTree(points[road,:2]).query(points[candidates,:2])[0]<1
                candidates=candidates[near]
                with np.load(ROOT/'data/evaluation_cache'/f'08-{frame:06d}-{sig}.npz') as z:classes=z['classes'];confidence=z['confidence']
                if len(candidates):
                    bad=candidates[classes[candidates]!=truth[candidates]];anchor=points[bad[0] if len(bad) else candidates[0],:3]
                    crop=np.flatnonzero(np.linalg.norm(points[:,:2]-anchor[:2],axis=1)<4);crop=crop[np.linspace(0,len(crop)-1,min(2500,len(crop)),dtype=int)]
                    f.update(anchor=anchor.tolist(),points=np.c_[points[crop,:3],classes[crop],truth[crop],confidence[crop]].round(4).tolist(),target_points=len(candidates),error_fraction=float(np.mean(classes[candidates]!=truth[candidates])),scope='GT sidewalk points within 1m XY of GT road; semantic adjacency proxy, not surveyed curb height')
    path.write_text(json.dumps(r,separators=(',',':')))
    u=r['modes']['uniform'];p=r['modes']['prism']
    lines=[f'# PRISM finalist evidence — {date.today().isoformat()}','',f"Evaluated **{len(rows)} / 4,071 sequence-08 scans**. Sequence 08 remains validation, used for checkpoint/runtime selection. Untouched sequence 11: **{r['test']['frames']} scans**, runtime only; official test labels are private.",'',f"Checkpoint epoch {r['model']['epoch']}, SHA-256 `{r['model']['sha256']}`. Hardware: {r['hardware']}.",'','## What the measurements prove','',f"PRISM uses {p['cells']:,.0f} occupied leaves versus {u['cells']:,.0f} uniform ({100*(1-p['cells']/u['cells']):.2f}% fewer). Leaf storage {u['bytes']/1048576:.3f} → {p['bytes']/1048576:.3f} MiB. Grid time {u['grid_ms']:.2f} → {p['grid_ms']:.2f} ms. This is an allocation/accuracy trade-off, not a blanket speed win.",'',f"Near common-cell mIoU {u['bands'][0]['common_5cm_cell']['miou']*100:.3f}% → {p['bands'][0]['common_5cm_cell']['miou']*100:.3f}%. Model+grid {p['fps']:.3f} FPS. The prototype is an offline demonstrator, not a production real-time autonomous stack.",'','| Policy | Near common-cell mIoU | Cells | Leaf MiB | Grid ms | Model+grid FPS |','|---|---:|---:|---:|---:|---:|']
    for mode,v in r['modes'].items():lines.append(f"| {mode} | {v['bands'][0]['common_5cm_cell']['miou']*100:.3f}% | {v['cells']:,.0f} | {v['bytes']/1048576:.3f} | {v['grid_ms']:.2f} | {v['fps']:.3f} |")
    lines+=['','## Runtime', '',r['runtime_scope'],'',f"Cold first full result: {r['cold_start_ms']:.1f} ms, including {r['checkpoint_load_ms']:.1f} ms checkpoint load.",'','| Stage/resource | P50 | P95 | P99 | n |','|---|---:|---:|---:|---:|']
    for k,v in r['runtime'].items():lines.append(f"| {k} | {v['p50']:.2f} | {v['p95']:.2f} | {v['p99']:.2f} | {v['n']} |")
    lines+=['','## Definitions and limitations','', 'Own-cell GT: majority of nonignored SemanticKITTI GT labels inside each predicted grid leaf. Common-cell GT: majority label on fixed occupied 5cm support. The latter prevents changing evaluation units from gaming the score. Confusion matrices include an unknown-prediction column.','','Elevation MAE/RMSE/P95 compare adaptive means with the raw-scan GT 5cm leaf means on common support; reported summaries macro-average per-frame error statistics. This measures projection/compression error, not independently surveyed terrain accuracy. Min/max errors are in per-frame JSON. Occupancy is observed obstacle-semantic IoU; unobserved space is never scored as free.','','Boundary distance is a mixed-GT-cell edge proxy, not annotated curb accuracy. No surveyed curb heights are available. Temporal overlap is ego-compensated nearest-cell matching for consecutive frames only. It is not tracking precision, ID switches or velocity error.','','CIs use paired circular moving-block bootstrap (16 evaluated frames, 1,000 draws), accounting partly for temporal correlation. They do not establish independent-sequence generalization. Composition strata are measured GT proportions; urban/highway/residential/weather tags are not invented.','','Tracking roadmap: annotate/validate associations against instance IDs with dynamic/static motion GT, implement lifecycle-managed tracks and odometry propagation, then score association precision/recall, ID switches and velocity error. Current boxes are Dynamic-object semantic segmentation, not certified motion tracks.','','## UI and deployment','','The four views share frame and camera. The voxel pane renders occupied surfaces from an actually allocated 20×20×4m dense 5cm crop; outer space is not claimed as allocated. Adaptive full-cloud counts and leaf bytes are measured independently of rendering caps. Confidence, variance, height span, GT-error and observed/unobserved modes use real arrays. Three challenge crops show prediction and GT side-by-side.','','The focus heading now travels browser → validated API → both full/local PRISM builds. Ellipse math matches the engine. A turn response audit is included in the JSON. Browser response shows end-to-end request time, separate from measured grid time.','','Trained model download includes two fixed-N TorchScript exports (4096,1024), trained checkpoint, source, class YAML, feature contract and numerical parity results. Batch 1 and 2 parity tested on RTX 2060 Super; no TensorRT/Jetson performance certification.','','All evidence: `data/grid_evidence.json`; deployment checks: `data/deployment/manifest.json`.']
    (ROOT/'docs/reports').mkdir(parents=True,exist_ok=True)
    (ROOT/'docs/reports/finalist-evidence.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');print('Finalist report and summaries saved')
if __name__=='__main__':main()

