"""Exercise real offline jobs for each supported file family against local API."""
from pathlib import Path
import json,time,zipfile,io
import numpy as np,requests
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'data/upload_fixtures';folder.mkdir(exist_ok=True)
rng=np.random.default_rng(42)
points=np.c_[rng.uniform(1,8,2000),rng.uniform(-4,4,2000),np.full(2000,-1.7),rng.uniform(0,1,2000)].astype('float32')
points.tofile(folder/'single.bin')
import open3d as o3d
cloud=o3d.geometry.PointCloud();cloud.points=o3d.utility.Vector3dVector(points[:,:3])
for ext in ['ply','pcd']:o3d.io.write_point_cloud(str(folder/f'single.{ext}'),cloud)
with zipfile.ZipFile(folder/'sequence.zip','w') as z:
    for i in range(2):z.writestr(f'{i:06d}.bin',points.tobytes())
results=[]
for name in ['single.bin','single.ply','single.pcd','sequence.zip']:
    with (folder/name).open('rb') as f:r=requests.post('http://127.0.0.1:8000/api/jobs',files={'files':(name,f)},timeout=30)
    r.raise_for_status();job=r.json();deadline=time.monotonic()+120;partial=False
    while time.monotonic()<deadline:
        job=requests.get(f'http://127.0.0.1:8000/api/jobs/{job["id"]}',timeout=30).json()
        if job['completed'] and job['status']=='processing':partial=True
        if job['status'] in ('complete','failed'):break
        time.sleep(.2)
    assert job['status']=='complete',job
    frame=requests.get(f'http://127.0.0.1:8000/api/jobs/{job["id"]}/frames/0',timeout=30).json()
    assert frame['grids']['prism']['active_cells']>0 and len(frame['weightage'])==4
    results.append({'format':name,'frames':job['completed'],'status':job['status'],'processing_fps':job['processing_fps'],'partial_observed':partial,'checkpoint':frame['timing']['model']['sha256'],'fixture':'synthetic parser fixture; not an accuracy evaluation'})
    print(name,job['status'],job['completed'],flush=True)
(ROOT/'data/upload_verification.json').write_text(json.dumps(results,indent=2))
