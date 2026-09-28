import numpy as np
from backend.grid_engine.ndtree import NdTree,CONFIGS
from backend.eval.grid_quality import quality,paired_ci
from backend.eval.metrics import confusion,scores

def test_cell_votes_and_height_error_use_common_support():
    points=np.array([[70.02,.02,0,1],[70.12,.02,.2,1],[70.22,.02,0,1]])
    truth=np.array([0,0,2],np.uint8);pred=np.array([0,0,0],np.uint8)
    ref=NdTree('uniform').build(points,truth)
    coarse=NdTree('distance').build(points,pred)
    q=quality(points,truth,coarse,ref)['bands'][3]
    assert q['cell']['labeled_points']==1
    assert q['common_5cm_cell']['labeled_points']==3
    assert q['cell']['accuracy']==1
    assert np.isclose(q['common_5cm_cell']['accuracy'],2/3)
    assert q['elevation']['mae']>0
    assert quality(points,truth,ref,ref)['bands'][3]['elevation']['mae']==0

def test_heading_changes_real_allocation_at_speed():
    x,y=np.meshgrid(np.arange(-35,35,.2),np.arange(-35,35,.2))
    points=np.c_[x.ravel(),y.ravel(),np.zeros(x.size)]
    labels=np.zeros(len(points),np.uint8)
    a=NdTree().build(points,labels,speed=16,heading=0)
    b=NdTree().build(points,labels,speed=16,heading=np.pi/2)
    assert not np.array_equal(a.nodes,b.nodes)
    for g in (a,b):
        assert np.allclose(g.nodes['size'][np.hypot(g.nodes['x'],g.nodes['y'])<2.9],.05)

def test_ground_and_semantic_ablation_are_distinct():
    points=np.array([[40.02,.02,0],[40.12,.02,0],[40.22,.02,0]])
    labels=np.array([0,0,3],np.uint8)
    assert 'semantic' in CONFIGS
    assert len(NdTree('semantic').build(points,labels).nodes)>len(NdTree('ground').build(points,labels).nodes)

def test_class_recall_and_paired_interval():
    out=scores(confusion(np.array([0,3,3],np.uint8),np.array([0,0,3],np.uint8)))
    assert out['recall'][3]==.5 and out['precision'][3]==1
    ci=paired_ci([1]*32,[2]*32)
    assert ci['low']==ci['high']==ci['delta']==1
