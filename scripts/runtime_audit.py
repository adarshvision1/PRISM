"""Actual production process_frame + serialization, isolated from evaluation overhead."""
import sys,json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np,torch,psutil
from backend.application.perception_pipeline import process_frame
from backend.model.pointnet_inference import PointNetPredictor
from backend.labels import read_scan
from backend.localization.odometry import world_pose
from backend.eval.grid_quality import distribution

def main():
    paths=sorted((ROOT/'data/dataset/sequences/08/velodyne').glob('*.bin'));paths=[paths[i] for i in np.linspace(0,len(paths)-1,32,dtype=int)]
    start=time.perf_counter();p=PointNetPredictor();load=(time.perf_counter()-start)*1000
    def source(path):
        i=int(path.stem);return {'points':read_scan(path),'pose':world_pose('08',i),'timestamp':i*.1,'name':f'08/{path.stem}','domain':'SemanticKITTI validation'}
    cold=source(paths[0]);tick=time.perf_counter();f,_=process_frame(p,cold);json.dumps(f);cold_ms=(time.perf_counter()-tick)*1000+load
    rows=[]
    for path in paths:
        src=source(path)
        if torch.cuda.is_available():torch.cuda.reset_peak_memory_stats()
        tick=time.perf_counter();f,_=process_frame(p,src)
        encode=time.perf_counter();json.dumps(f,separators=(',',':'));serialization=(time.perf_counter()-encode)*1000
        total=(time.perf_counter()-tick)*1000
        row={k:v for k,v in f['timing'].items() if k.endswith('_ms')}
        row.update(serialization_ms=serialization,total_pipeline_ms=total,grid_ms=f['grids']['prism']['grid_ms'],uniform_grid_ms=f['grids']['uniform']['grid_ms'],rss_mb=psutil.Process().memory_info().rss/1048576,
                   gpu_peak_allocated_mb=torch.cuda.max_memory_allocated()/1048576 if torch.cuda.is_available() else 0,gpu_peak_reserved_mb=torch.cuda.max_memory_reserved()/1048576 if torch.cuda.is_available() else 0)
        rows.append(row)
    report=json.loads((ROOT/'data/grid_evidence.json').read_text())
    if report['model']['sha256'] != p.metadata['sha256']:
        raise RuntimeError('Runtime checkpoint differs from grid evidence. Refresh grid evidence first.')
    report['runtime_model']=p.metadata
    report['ablation_stage_runtime']=report['runtime'];report['runtime']={k:distribution([r[k] for r in rows]) for k in rows[0]};report['cold_start_ms']=cold_ms;report['checkpoint_load_ms']=load
    report['runtime_scope']='32 spread validation scans, actual process_frame (both display grids + object clustering + curb ribbons) plus JSON serialization. Input disk read, compressed cache write, HTTP and browser excluded. CPU RSS sampled after frame; GPU allocator peak reset per frame.'
    report['runtime_frames']=[int(p.stem) for p in paths]
    (ROOT/'data/grid_evidence.json').write_text(json.dumps(report,separators=(',',':')))
    (ROOT/'data/runtime_audit.json').write_text(json.dumps({'scope':report['runtime_scope'],'cold_ms':cold_ms,'rows':rows},indent=2));print(json.dumps(report['runtime']['total_pipeline_ms']))
if __name__=='__main__':main()
