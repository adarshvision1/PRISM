"""Loopback-only offline API. No live devices, cloud services, or telemetry."""
import json, os, uuid
from fastapi import FastAPI,UploadFile,File,HTTPException,Request
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from backend.labels import ROOT,read_scan
from backend.ingest.upload_job_manager import JobManager
from backend.ingest.kitti_loader import SUPPORTED
from backend.infrastructure.config import config
from backend.infrastructure.paths import paths
from backend.application.evidence_service import EvidenceService
from backend.application.fusion_service import FusionService
from backend.application.model_service import require_ready
from backend.api.models import router as model_router
from backend.application.comparison_service import ComparisonService
app=FastAPI(title='PRISM Offline',version='2.0');manager=JobManager();evidence_service=EvidenceService();fusion_service=FusionService()
app.include_router(model_router)
app.state.comparisons=ComparisonService(manager)
def validate_architecture(architecture):
    try:require_ready(architecture)
    except ValueError as exc:raise HTTPException(409,str(exc)) from exc
app.mount('/assets',StaticFiles(directory=paths.frontend_assets),name='assets')
@app.middleware('http')
async def local_only(request:Request,call_next):
    try: content_length=int(request.headers.get('content-length','0'))
    except ValueError: return JSONResponse({'detail':'Invalid Content-Length'},status_code=400)
    if content_length>config.max_upload_bytes+1024**2:
        return JSONResponse({'detail':'Combined upload exceeds 500 MB'},status_code=413)
    if request.method not in ('GET','HEAD'):
        origin=request.headers.get('origin')
        allowed={item.strip().rstrip('/') for item in os.getenv('PRISM_ALLOWED_ORIGINS','').split(',') if item.strip()}
        allowed.update(('http://127.0.0.1:8000','http://localhost:8000',str(request.base_url).rstrip('/')))
        if origin and origin.rstrip('/') not in allowed:return JSONResponse({'detail':'Request origin is not allowed'},status_code=403)
    response=await call_next(request)
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'"
    return response
@app.get('/api/health')
def health():
    return {'status':'ready','offline':True,'checkpoint_ready':(ROOT/config.checkpoint).exists(),'interim_ready':(ROOT/config.interim_checkpoint).exists(),'upload_limit_mb':config.max_upload_mb,'frame_limit':config.max_frames}
@app.get('/api/evidence')
def evidence():
    return evidence_service.get_evidence()
@app.post('/api/jobs')
async def upload(files:list[UploadFile]=File(...),architecture:str='pointnet2'):
    validate_architecture(architecture)
    if not files or len(files)>config.max_frames:raise HTTPException(400,f'Choose 1–{config.max_frames} files. '+SUPPORTED)
    suffixes={'.bin','.ply','.pcd','.zip'}
    from pathlib import Path
    if any(Path(f.filename or '').suffix.lower() not in suffixes for f in files):raise HTTPException(415,'Supported: '+SUPPORTED)
    if len(files)>1 and any(Path(f.filename).suffix.lower()=='.zip' for f in files):raise HTTPException(400,'Upload one archive or multiple individual frames')
    folder=paths.jobs/uuid.uuid4().hex;folder.mkdir(parents=True);uploaded_paths=[];total=0
    try:
        for i,file in enumerate(files):
            name=Path(file.filename.replace('\\','/')).name;path=folder/f'{i:04d}-{name}';uploaded_paths.append(path)
            with path.open('wb') as out:
                while chunk:=await file.read(1024*1024):
                    total+=len(chunk)
                    if total>config.max_upload_bytes:raise HTTPException(413,f'Combined upload exceeds {config.max_upload_mb} MB')
                    out.write(chunk)
            await file.close()
    except Exception:
        for path in uploaded_paths:path.unlink(missing_ok=True)
        raise
    return manager.create(uploaded_paths,folder,architecture=architecture)
def safe_id(job_id):
    if len(job_id)!=32 or any(c not in '0123456789abcdef' for c in job_id):raise HTTPException(404,'Unknown job')
@app.get('/api/jobs/{job_id}')
def job(job_id:str):
    safe_id(job_id)
    try:return manager.get(job_id)
    except KeyError:raise HTTPException(404,'Unknown job')
@app.post('/api/jobs/{job_id}/cancel')
def cancel(job_id:str):
    safe_id(job_id)
    if job_id in manager.jobs:manager.jobs[job_id]['status']='cancelled'
    return job(job_id)
@app.get('/api/jobs/{job_id}/frames/{index}')
def frame(job_id:str,index:int):
    safe_id(job_id);path=paths.jobs/job_id/f'frame-{index:05d}.json'
    if index<0 or not path.exists():raise HTTPException(404,'Frame not completed yet')
    return FileResponse(path)
@app.get('/api/demo/{index}')
def demo(index:int):
    path=paths.pointnet_frames/f'{index:05d}.json'
    if index<0 or not path.exists():raise HTTPException(404,'Demo frame unavailable')
    return FileResponse(path)
@app.post('/api/sample')
def sample(chunk:int=0,architecture:str='pointnet2'):
    validate_architecture(architecture)
    from backend.localization.odometry import world_pose
    manifest=json.loads(paths.demo_manifest.read_text())['chunks']
    if not 0<=chunk<len(manifest):raise HTTPException(400,'Unknown sequence-08 interval')
    scan_paths=[paths.dataset/'sequences/08/velodyne'/f'{i:06d}.bin' for i in manifest[chunk]['frame_ids']]
    def source():
        for path in scan_paths:
            i=int(path.stem);yield {'points':read_scan(path),'pose':world_pose('08',i),'timestamp':i*.1,'name':f'08/{path.stem}','domain':'SemanticKITTI validation 08','rgb':None}
    folder=paths.jobs/uuid.uuid4().hex;folder.mkdir(parents=True)
    return manager.create([],folder,source(),architecture=architecture)
from pydantic import BaseModel,Field
class FusionRequest(BaseModel):
    demo_index:int=Field(default=0,ge=0,le=299)
    speed_kmh:float=Field(default=0,ge=0,le=60)
    heading:float=Field(default=0,ge=-3.141593,le=3.141593)
    job_id:str|None=None
    frame_index:int=Field(default=0,ge=0,le=299)
@app.post('/api/fusion')
def regrid(body:FusionRequest):
    if body.job_id:safe_id(body.job_id)
    try:return fusion_service.regrid(manager,body.demo_index,body.speed_kmh,body.job_id,body.frame_index,heading=body.heading)
    except (ValueError,FileNotFoundError) as exc:raise HTTPException(400,str(exc))
@app.get('/api/presets')
def presets():
    chunks=json.loads(paths.demo_manifest.read_text())['chunks']
    return [{'id':i,'name':f'Sequence 08 · interval {i+1:02d}','frames':len(c['frame_ids']),'start':c['frame_ids'][0],'end':c['frame_ids'][-1]} for i,c in enumerate(chunks)]
@app.get('/api/grid-evidence')
def grid_evidence():
    path=paths.grid_evidence
    if not path.exists():return {'status':'pending'}
    data=json.loads(path.read_text());data.pop('per_frame',None)
    return data
@app.get('/api/compute-evidence')
def compute_evidence():
    path=paths.root/'data/performance_trials.json'
    if not path.exists():return {'status':'pending'}
    data=json.loads(path.read_text())
    def summary(name):
        profile=data['profiles'].get(name)
        if not profile:return None
        return {'network_points':profile['mean']['network_points'],'fps':profile['fps'],'miou':profile['miou']}
    return {'status':'complete','frames':len(data['frames']),'scope':data['scope'],'reference':summary('reference'),'foveated':summary('foveated1024')}
@app.get('/api/grid-evidence/download')
def download_grid_evidence():
    path=paths.grid_evidence
    if not path.exists():raise HTTPException(404,'Evaluation not available')
    return FileResponse(path,filename='PRISM-grid-evidence.json')
@app.get('/api/model/download')
def model_download():
    from backend.application.model_service import describe
    if not describe('pointnet2')['download_ready']:raise HTTPException(409,'Export the current best PointNet++ checkpoint before downloading')
    path=paths.deployment_model
    if not path.exists():raise HTTPException(503,'Deployment export has not completed')
    return FileResponse(path,filename=path.name,media_type='application/zip')
@app.get('/')
@app.get('/README')
@app.get('/Benchmark')
@app.get('/Launch Model')
@app.get('/Launch')
@app.get('/benchmark')
@app.get('/launch')
def page():return FileResponse(paths.frontend_index)
