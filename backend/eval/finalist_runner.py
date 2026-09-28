"""Reproducible grid evidence, five ablations, paired uncertainty and failure crops."""
import argparse,json,time,hashlib,platform
import numpy as np
import torch,psutil
from backend.labels import ROOT,read_scan,read_truth,config
from backend.grid_engine.ndtree import NdTree,CONFIGS
from backend.model.pointnet_inference import PointNetPredictor
from backend.localization.odometry import motion,world_pose
from backend.detection.clustering import object_boxes
from backend.eval.metrics import confusion,scores
from backend.eval.grid_quality import quality,distribution,paired_ci,temporal,BANDS

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=1024);ap.add_argument('--test-limit',type=int,default=0);ap.add_argument('--skip-test',action='store_true');args=ap.parse_args()
    start=time.perf_counter();predictor=PointNetPredictor();load_ms=(time.perf_counter()-start)*1000
    paths=sorted(p for p in (ROOT/'data/dataset/sequences/08/velodyne').glob('*.bin') if (p.parent.parent/'labels'/f'{p.stem}.label').exists())
    paths=[paths[i] for i in np.linspace(0,len(paths)-1,min(args.limit,len(paths)),dtype=int)]
    if not paths:raise RuntimeError('No validation data')
    cold_start=time.perf_counter();predictor.predict(read_scan(paths[0]));cold_ms=(time.perf_counter()-cold_start)*1000+load_ms
    if torch.cuda.is_available():torch.cuda.reset_peak_memory_stats()
    rows=[];failures={};previous=None;previous_pose=None;previous_id=None;process=psutil.Process()
    point_cm={m:[np.zeros((4,5),np.int64) for _ in BANDS] for m in CONFIGS}
    cell_cm={m:[np.zeros((4,5),np.int64) for _ in BANDS] for m in CONFIGS};common_cm={m:[np.zeros((4,5),np.int64) for _ in BANDS] for m in CONFIGS}
    cfg=config();raw_names=cfg['labels'];cache=ROOT/'data/evaluation_cache';cache.mkdir(exist_ok=True)
    sig=hashlib.sha256((predictor.metadata['sha256']+json.dumps(predictor.metadata['runtime'],sort_keys=True)).encode()).hexdigest()[:16]
    for i,path in enumerate(paths):
        points=read_scan(path);truth=read_truth(path.parent.parent/'labels'/f'{path.stem}.label');tick=time.perf_counter()
        classes,confidence,timing,_=predictor.predict(points)
        np.savez_compressed(cache/f'08-{path.stem}-{sig}.npz',classes=classes,confidence=confidence)
        speed,heading=motion('08',int(path.stem));pose=world_pose('08',int(path.stem));radius=np.linalg.norm(points[:,:2],axis=1)
        # GT reference uses identical observed points, with majority GT labels.
        reference=NdTree('uniform').build(points,truth)
        row={'frame':int(path.stem),'timing':{k:v for k,v in timing.items() if k.endswith('_ms')},'modes':{},'rss_mb':process.memory_info().rss/1048576}
        for mode in CONFIGS:
            grid=NdTree(mode).build(points,classes,confidence,speed=speed,heading=heading)
            q=quality(points,truth,grid,reference);q['point_bands']=[]
            for j,(lo,hi) in enumerate(BANDS):
                cm=confusion(truth,grid.point_classes,(radius>=lo)&(radius<hi));point_cm[mode][j]+=cm;q['point_bands'].append(scores(cm))
                cell_cm[mode][j]+=np.asarray(q['bands'][j]['cell']['confusion']);common_cm[mode][j]+=np.asarray(q['bands'][j]['common_5cm_cell']['confusion'])
            row['modes'][mode]=q
            if mode=='prism':
                if previous_id is not None and int(path.stem)==previous_id+1:row['temporal']=temporal(previous,grid,previous_pose,pose)
                previous,previous_pose,previous_id=grid,pose,int(path.stem)
        tick=time.perf_counter();boxes=object_boxes(points,classes,confidence);row['timing']['detection_ms']=(time.perf_counter()-tick)*1000
        tick=time.perf_counter();payload=json.dumps({'cells':previous.wire(16000),'boxes':boxes,'points':points[::10].tolist()},separators=(',',':'));row['timing']['serialization_ms']=(time.perf_counter()-tick)*1000
        row['timing']['total_pipeline_ms']=timing['inference_ms']+row['modes']['prism']['grid_ms']+row['timing']['detection_ms']+row['timing']['serialization_ms']
        row['gpu_allocated_mb']=torch.cuda.memory_allocated()/1048576 if torch.cuda.is_available() else 0
        row['gpu_reserved_mb']=torch.cuda.memory_reserved()/1048576 if torch.cuda.is_available() else 0
        # Composition strata are measured, not invented urban/weather annotations.
        dyn=float(np.mean(truth==3));terrain=float(np.mean(truth==1));static=float(np.mean(truth==2))
        row['scene_stratum']='dense-object' if dyn>.12 else ('structure-dominant' if static>.5 else ('terrain-dominant' if terrain>.3 else 'mixed-road'))
        raw=np.fromfile(path.parent.parent/'labels'/f'{path.stem}.label',dtype='<u4')&65535
        groups={'far pedestrian':np.array([k for k,v in raw_names.items() if 'person' in v or 'bicyclist' in v]),'thin pole / sign':np.array([k for k,v in raw_names.items() if v in ('pole','traffic-sign')]),'curb / sidewalk boundary':np.array([k for k,v in raw_names.items() if v=='sidewalk'])}
        for name,labels in groups.items():
            mask=np.isin(raw,labels)&(truth<4)&(radius<100)
            if name=='far pedestrian':mask &= radius>25
            if mask.sum()<2:continue
            error=float(np.mean(classes[mask]!=truth[mask]));candidate=error+min(mask.sum(),100)/1000
            if name in failures and failures[name]['rank']>=candidate:continue
            bad=np.flatnonzero(mask&(classes!=truth));anchor=points[bad[0] if len(bad) else np.flatnonzero(mask)[0],:3]
            near=np.flatnonzero(np.linalg.norm(points[:,:2]-anchor[:2],axis=1)<4);near=near[np.linspace(0,len(near)-1,min(2500,len(near)),dtype=int)]
            failures[name]={'name':name,'frame':int(path.stem),'rank':candidate,'target_points':int(mask.sum()),'error_fraction':error,'anchor':anchor.tolist(),'points':np.c_[points[near,:3],classes[near],truth[near],confidence[near]].round(4).tolist(),'scope':'GT-selected challenge crop; worst observed candidate, not representative accuracy'}
        rows.append(row)
        if i%5==0:print('Grid evidence',i+1,'/',len(paths),flush=True)
    modes={}
    for mode in CONFIGS:
        entries=[r['modes'][mode] for r in rows]
        out={k:float(np.mean([e[k] for e in entries if e[k] is not None])) if any(e[k] is not None for e in entries) else None for k in ('cells','bytes','grid_ms','refinement_ops','retained_fraction','complex_region_mean_cell_m','simple_region_mean_cell_m')}
        out['fps']=1000/np.mean([r['timing']['inference_ms']+r['modes'][mode]['grid_ms'] for r in rows]);out['grid_latency']=distribution([e['grid_ms'] for e in entries]);out['bands']=[]
        for j in range(4):
            band={'distance_m':list(BANDS[j]),'cell':scores(cell_cm[mode][j]),'common_5cm_cell':scores(common_cm[mode][j]),'point':scores(point_cm[mode][j])}
            for k in ('cells','bytes','observed_obstacle_iou'):
                values=[e['bands'][j][k] for e in entries if e['bands'][j][k] is not None];band[k]=float(np.mean(values)) if values else None
            band['elevation']={k:float(np.mean([e['bands'][j]['elevation'][k] for e in entries if e['bands'][j]['elevation'][k] is not None])) if any(e['bands'][j]['elevation'][k] is not None for e in entries) else None for k in ('mae','rmse','p95')}
            band['histogram']={str(s):sum(e['bands'][j]['histogram'][str(s)] for e in entries) for s in (.05,.1,.25,.5)}
            band['area_m2']={str(s):sum(e['bands'][j]['observed_leaf_area_m2'][str(s)] for e in entries) for s in (.05,.1,.25,.5)}
            out['bands'].append(band)
        modes[mode]=out
    pairs={k:paired_ci([r['modes']['uniform'][k] for r in rows],[r['modes']['prism'][k] for r in rows]) for k in ('cells','bytes','grid_ms')}
    pairs['near_cell_miou']=paired_ci([r['modes']['uniform']['bands'][0]['common_5cm_cell']['miou'] for r in rows],[r['modes']['prism']['bands'][0]['common_5cm_cell']['miou'] for r in rows])
    runtime={k:distribution([r['timing'][k] for r in rows]) for k in rows[0]['timing']};runtime['grid_ms']=modes['prism']['grid_latency']
    for k in ('rss_mb','gpu_allocated_mb','gpu_reserved_mb'):runtime[k]=distribution([r[k] for r in rows])
    strata={s:{'frames':sum(r['scene_stratum']==s for r in rows),'prism_cell_miou':float(np.mean([np.mean([b['cell']['miou'] for b in r['modes']['prism']['bands'] if b['cell']['miou'] is not None]) for r in rows if r['scene_stratum']==s]))} for s in sorted({r['scene_stratum'] for r in rows})}
    # Never tune on official test 11. Its labels are private: runtime only.
    testpaths=[] if args.skip_test else sorted((ROOT/'data/dataset/sequences/11/velodyne').glob('*.bin'))
    if args.test_limit:
        testpaths=[testpaths[i] for i in np.linspace(0,len(testpaths)-1,min(args.test_limit,len(testpaths)),dtype=int)]
    testtimes=[]
    for i,p in enumerate(testpaths):
        points=read_scan(p);c,co,t,_=predictor.predict(points);g=NdTree('prism').build(points,c,co);testtimes.append(t['inference_ms']+g.elapsed_ms)
        if i%50==0:print('Untouched test 11 runtime',i+1,'/',len(testpaths),flush=True)
    report={'status':'complete','frames':len(rows),'model':predictor.metadata,'hardware':torch.cuda.get_device_name(0) if torch.cuda.is_available() else platform.processor(),'cold_start_ms':cold_ms,'checkpoint_load_ms':load_ms,'runtime_scope':f'{len(rows)} spread sequence-08 scans: segmentation preprocessing, network, point reassembly, PRISM grid, object clustering and JSON serialization. Input disk read, upload-job cache writes, HTTP and browser rendering are excluded. Sequence-11 run is runtime-only and sampled separately.','modes':modes,'paired_ci':pairs,'runtime':runtime,'scene_strata':strata,'failure_gallery':list(failures.values()),'per_frame':rows,
      'test':{'sequence':'11','frames':len(testtimes),'label_status':'Private official test labels. No local accuracy score; never used for training or tuning.','pipeline_ms':distribution(testtimes)},
      'limitations':{'weather_lighting':'No verified per-frame metadata available; no invented strata.','tracking':'No validated tracker. ID switches, tracking precision/recall and velocity error unavailable.','curb_height_error':'No surveyed curb ground truth. Elevation metrics are compression error against raw-scan 5cm GT statistics.','occupancy':'Observed obstacle-semantic IoU only; no free-space ray ground truth.','elevation':'Macro-averaged per-frame elevation errors against raw LiDAR fine-cell stats; not independent surveyed elevation truth.','scene_types':'GT composition strata, not verified urban/highway/residential tags.','coverage':'Sequence 08 is validation and was used for checkpoint/runtime selection. Paired CIs use moving-block bootstrap; not an untouched test score.','boundary':'Per-frame boundary_incell_distance is a mixed-GT-cell boundary proxy, not annotated curb distance.','temporal':'Only consecutive scanned frames with poses; nearest-cell overlap proxy, not object tracking.'}}
    (ROOT/'data/grid_evidence.json').write_text(json.dumps(report,separators=(',',':'),allow_nan=False));print('Saved grid_evidence.json',flush=True)
if __name__=='__main__':main()
