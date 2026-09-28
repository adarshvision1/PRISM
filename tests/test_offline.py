import io,json,zipfile,time
from pathlib import Path
import numpy as np
import pytest
import torch
from backend.grid_engine.split_tests import semantic_split
from backend.model.preprocess import blocks,ground_height,pose_residual
from backend.model.losses import ace_lovasz
from backend.model.pointnet2.network import PointNet2MSG
from backend.detection.clustering import object_boxes,attach_tracks
from backend.ingest.kitti_loader import iter_upload,validate_archive
from backend.eval.metrics import confusion,scores
from backend.api.server import app
from fastapi.testclient import TestClient

def test_small_entropy_and_large_chi_square():
    assert semantic_split([[10,0,0,0],[4,3,3,0],[1000,0,0,0],[700,100,100,100]]).tolist()==[False,True,False,True]
def test_resampling_and_ground_preserve_coordinates():
    rng=np.random.default_rng(1);p=np.c_[rng.uniform(0,30,(400,2)),np.full(400,-1.7),rng.uniform(0,1,400)]
    h,plane,valid=ground_height(p);assert valid;assert np.max(np.abs(h))<1e-5
    f=np.c_[p,h,np.zeros(len(p))];result=list(blocks(f))
    assert sum(b['original_count'] for b in result)==len(p)
    assert all(b['features'].shape==(4096,6) for b in result)
    for b in result:
        reconstructed=b['features'][:,:3]+b['offset']
        assert np.max(np.abs(reconstructed-p[b['sample_indices'],:3]))<.02
def test_pose_compensation_removes_ego_motion():
    p=np.array([[10,2,0,0],[12,3,0,0]],np.float32);pose=np.eye(4);pose[0,3]=1
    current=p.copy();current[:,0]-=1;r,available=pose_residual(current,p,pose,np.eye(4))
    assert available and np.max(r)<1e-6
    assert not pose_residual(p)[1]
def test_sparse_object_never_disappears():
    p=np.array([[30,0,1,0],[70,2,1,0]],float);boxes=object_boxes(p,np.array([3,3]),np.array([.8,.7]))
    assert len(boxes)==2 and all(b['fallback'] for b in boxes)
    assert sum(b['points'] for b in boxes)==2
def test_tracks_require_pose():
    old=[{'class':3,'fallback':False,'center':[10,0,0]}];new=[{'class':3,'fallback':False,'center':[9,0,0],'trail':None}]
    attach_tracks(new,old,None,None);assert new[0]['trail'] is None
    pose=np.eye(4);pose[0,3]=1;attach_tracks(new,old,pose,np.eye(4));assert new[0]['displacement_m']==0
def test_loss_finite_on_ignored_and_imbalanced_labels():
    x=torch.randn(2,4,64,requires_grad=True);y=torch.zeros(2,64,dtype=torch.long);y[0,:2]=3;y[1,0]=255
    loss=ace_lovasz(x,y);loss.backward();assert torch.isfinite(loss) and torch.isfinite(x.grad).all()
def test_unknown_prediction_counts_as_error():
    cm=confusion(np.array([0,3,255]),np.array([0,255,3]));result=scores(cm)
    assert result['iou'][3]==0 and result['miou']==.5 and result['labeled_points']==2
def test_zip_traversal_rejected(tmp_path):
    p=tmp_path/'bad.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('../escape.bin',b'bad')
    with pytest.raises(ValueError,match='Unsafe'):validate_archive(p)
def test_offline_routes_and_bad_upload():
    with TestClient(app) as client:
        for page in ['/README','/Benchmark','/Launch%20Model']:assert client.get(page).status_code==200
        assert client.get('/api/health').json()['offline'] is True
        assert client.post('/api/jobs',files={'files':('movie.mp4',b'not depth')}).status_code==415
        assert client.post('/api/sample',headers={'origin':'https://external.invalid'}).status_code==403
        assert client.get('/api/jobs/../../config.json').status_code==404
def test_best_checkpoint_matches_training_curve():
    from backend.labels import ROOT
    path=ROOT/'backend/model/weights/best.ckpt'
    if not path.exists():pytest.skip('No completed training run')
    import csv
    rows=list(csv.DictReader((ROOT/'docs/training_log.csv').open()));checkpoint=torch.load(path,map_location='cpu',weights_only=True)
    assert checkpoint['val_miou']==max(float(r['val_miou']) for r in rows)
    run=json.loads((ROOT/'data/training_run.json').read_text())
    assert run['best_epoch']==checkpoint['epoch']
    assert run['total_epochs_logged']==len(rows)
    model=PointNet2MSG(**checkpoint['model_config']);model.load_state_dict(checkpoint['state_dict'])

def test_resuming_best_checkpoint_keeps_training_epoch_ids_monotonic():
    from backend.model.train import next_epoch_index
    history=[{'epoch':str(epoch)} for epoch in range(1,25)]
    assert next_epoch_index(22,history)==24
    assert next_epoch_index(27,history)==27

def test_runtime_profile_selection_protects_near_field_class_recall():
    from scripts.profile_candidates import select_profiles
    def row(miou,fps,recall):return {'miou':miou,'fps':fps,'near':{'recall':recall}}
    report={'profiles':{
        'reference':row(.80,1.0,[.90,.80,.95,.89]),
        'foveated':row(.795,1.8,[.895,.80,.95,.90]),
        'compact':row(.794,2.1,[.90,.80,.95,.87]),
    }}
    assert select_profiles(report)['recommended']=='foveated'
def test_official_split_integrity():
    from backend.labels import ROOT,config
    manifest=json.loads((ROOT/'data/blocks_cache/manifest.json').read_text())
    train=set(manifest['train']['sequences']);valid=set(manifest['valid']['sequences'])
    assert train=={f'{s:02d}' for s in config()['split']['train']}
    assert valid=={'08'} and train.isdisjoint(valid)
