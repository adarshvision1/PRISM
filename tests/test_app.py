from fastapi.testclient import TestClient
from backend.api.server import app

def test_current_routes_and_preset_provenance():
    with TestClient(app) as c:
        for page in ['/','/README','/benchmark','/launch','/Benchmark','/Launch']:
            assert c.get(page).status_code==200
        presets=c.get('/api/presets').json()
        assert len(presets)==10 and all(p['frames']>0 for p in presets)
        evidence=c.get('/api/evidence').json()
        grid=c.get('/api/grid-evidence').json()
        assert evidence['benchmark']['model']['epoch']==30
        assert evidence['demo']['model']['sha256']==evidence['benchmark']['model']['sha256']
        # Point-level/full-backend evidence is the historical epoch-30 run;
        # the cell-level grid report is the newer epoch-48 checkpoint. Keep
        # their provenance distinct so newer training scores cannot inherit
        # older runtime measurements.
        assert evidence['benchmark']['model']['epoch']==30
        assert grid['frames']==256 and grid['model']['epoch']==48
        assert grid['model']['sha256'] != evidence['benchmark']['model']['sha256']
        assert c.post('/api/sample?chunk=999').status_code==400
        assert c.post('/api/fusion',json={'speed_kmh':61}).status_code==422
        assert c.post('/api/fusion',json={'job_id':'../outside'}).status_code==404

def test_dropped_formats_and_network_mutations_rejected():
    with TestClient(app) as c:
        assert c.post('/api/jobs',files={'files':('phone.r3d',b'bad')}).status_code==415
        assert c.post('/api/sample',headers={'origin':'https://outside.invalid'}).status_code==403
        assert c.get('/api/health',headers={'content-length':'bad'}).status_code==400
        assert c.get('/assets/app.js').status_code==404

def test_full_cloud_fusion_rebuilds_and_measures():
    with TestClient(app) as c:
        a=c.post('/api/fusion',json={'demo_index':0,'speed_kmh':0})
        b=c.post('/api/fusion',json={'demo_index':0,'speed_kmh':60})
        assert a.status_code==b.status_code==200
        a,b=a.json(),b.json()
        assert a['input_points']>14000 and b['prism']['grid_ms']>0
        assert a['prism']['cells']!=b['prism']['cells']
        assert a['voxel']['bytes']==12800000
        turned=c.post('/api/fusion',json={'demo_index':0,'speed_kmh':60,'heading':1.570796}).json()
        assert turned['heading']==1.570796
        assert turned['prism']['cells']!=b['prism']['cells']
        assert turned['changed_cells']>0
        assert c.post('/api/fusion',json={'heading':4}).status_code==422

def test_downloaded_model_bundle_contains_validated_deployment_contract():
    import io,zipfile,json,torch
    from backend.labels import ROOT
    with TestClient(app) as c:
        response=c.get('/api/model/download')
    assert response.status_code==200
    assert 'PRISM-trained-model.zip' in response.headers['content-disposition']
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names=set(archive.namelist())
        assert {'pointnet2-4096.torchscript.pt','pointnet2-1024.torchscript.pt','manifest.json','MODEL_CARD.md','backend/model/preprocess.py'} <= names
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['checkpoint']['epoch']==torch.load(ROOT/'backend/model/weights/best.ckpt',map_location='cpu',weights_only=True)['epoch']
        assert {row['device'] for row in manifest['parity_checks']}=={'cpu','cuda'}
