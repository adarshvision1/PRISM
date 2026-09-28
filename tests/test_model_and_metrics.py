import numpy as np
from backend.model.pointnet_inference import PointNetPredictor
from backend.labels import ROOT,read_scan

def test_real_checkpoint_full_scan_prediction():
    model=PointNetPredictor()
    points=read_scan(ROOT/'data/dataset/sequences/08/velodyne/000000.bin')
    classes,confidence,timing,features=model.predict(points)
    assert len(classes)==len(points)==len(confidence)
    assert np.isfinite(confidence).all() and np.all((confidence>=0)&(confidence<=1))
    assert len(np.unique(classes))>=3 and timing['network_ms']>0
    assert features.shape==(len(points),6)
    assert model.metadata['status'].startswith('trained')
