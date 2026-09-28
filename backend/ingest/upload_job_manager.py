import json,threading,time,uuid
import numpy as np
import psutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.model.inference import SegmentationPredictor
from backend.application.perception_pipeline import process_frame
from backend.infrastructure.config import config
from backend.infrastructure.jobs import JobRepository
from .kitti_loader import iter_upload
class JobManager:
    def __init__(self):
        self.jobs={};self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='prism');self.lock=threading.RLock();self.predictor=None;self.repository=JobRepository()
    def create(self,paths,folder,source_iterator=None,architecture='pointnet2'):
        job_id=folder.name
        record={'id':job_id,'status':'queued','completed':0,'total_limit':config.max_frames,'elapsed_seconds':0,'processing_fps':0,'error':None,'model':None}
        record['architecture']=architecture
        with self.lock:self.jobs[job_id]=record
        self.pool.submit(self._run,job_id,paths,folder,source_iterator)
        return dict(record)
    def _run(self,job_id,paths,folder,source_iterator):
        start=time.perf_counter();previous=None;record=self.jobs[job_id]
        try:
            record['status']='processing'
            # Freeze one checkpoint for the whole job; no mid-sequence hot swaps.
            with self.lock:
                self.predictor=None
                predictor=SegmentationPredictor(architecture=record['architecture'],freeze=True)
                self.predictor=predictor
            record['model']=dict(predictor.metadata)
            iterator=source_iterator if source_iterator is not None else iter_upload(paths,folder)
            for source in iterator:
                if record['status']=='cancelled':break
                frame_start=time.perf_counter()
                with self.lock:
                    result,previous=process_frame(predictor,source,previous,lambda stage:record.update(active_stage=stage))
                record['active_stage']='serialization'
                result['index']=record['completed'];target=folder/f'frame-{result["index"]:05d}.json'
                result['rss_mb']=psutil.Process().memory_info().rss/1048576
                np.savez_compressed(folder/f'source-{result["index"]:05d}.npz',points=source['points'],classes=previous['classes'],confidence=previous['confidence'])
                tick=time.perf_counter();json.dumps(result,separators=(',',':'))
                result['timing']['serialization_ms']=(time.perf_counter()-tick)*1000
                result['timing']['total_with_cache_ms']=(time.perf_counter()-frame_start)*1000
                target.write_text(json.dumps(result,separators=(',',':')))
                record['completed']+=1;record['elapsed_seconds']=time.perf_counter()-start;record['processing_fps']=record['completed']/record['elapsed_seconds']
                self.repository.save(folder,record)
            if record['status']!='cancelled':record['status']='complete'
        except Exception as exc:record['status']='failed';record['error']=f'{type(exc).__name__}: {exc}'
        finally:
            record['active_stage']=None
            record['elapsed_seconds']=time.perf_counter()-start;self.repository.save(folder,record)
    def get(self,job_id):
        if job_id in self.jobs:return dict(self.jobs[job_id])
        result=self.repository.load(job_id)
        if result is not None:
            if result['status'] in ('queued','processing'):result['status']='interrupted';result['error']='Server restarted; completed frames remain available.'
            return result
        raise KeyError(job_id)
