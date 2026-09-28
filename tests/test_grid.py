import numpy as np
import pytest
from backend.grid_engine.ndtree import NdTree, resolution_ceiling, SAFETY_FLOOR_RADIUS_M
from backend.labels import macro_lut, config

def test_official_mapping_complete_and_vehicle_conservative():
    lut=macro_lut()
    for code,name in config()['labels'].items():
        assert (lut[code] == 255) == config()['learning_ignore'][config()['learning_map'][code]]
        if name.startswith('moving-') or name in ('car','bus','on-rails','person','truck'): assert lut[code] == 3

def test_safety_floor_wins_at_any_heading_or_speed():
    rng=np.random.default_rng(1)
    p=rng.uniform(-3,3,(8000,3));p[:,2]=0
    p=p[np.linalg.norm(p[:,:2],axis=1)<SAFETY_FLOOR_RADIUS_M]
    for speed,heading in [(0,0),(80,np.pi),(15,-1.8)]:
        r=NdTree().build(p,np.zeros(len(p),np.uint8),speed=speed,heading=heading)
        assert np.allclose(r.nodes['size'],.05)

def test_fovea_rotates_and_changes_shape():
    xy=np.array([[18,0],[0,18],[-18,0]])
    assert resolution_ceiling(xy,25,0).tolist()==[.05,.1,.1]
    assert resolution_ceiling(xy,25,np.pi/2).tolist()==[.1,.05,.1]

def test_full_cell_ceiling_and_no_overlap():
    rng=np.random.default_rng(3)
    p=rng.uniform(-80,80,(18000,3));p[:,2]=0
    r=NdTree().build(p,np.zeros(len(p),np.uint8),speed=15,heading=.7)
    valid=r.point_cells>=0
    nodes=r.nodes[r.point_cells[valid]]
    assert np.all(nodes['size'] <= resolution_ceiling(p[valid,:2],15,.7)+1e-6)
    # Convert every occupied node footprint to minimum-grid keys; none may overlap.
    occupied=set()
    for node in r.nodes:
        x,y=np.rint([node['x']/ .05,node['y']/.05]).astype(int)
        width=int(round(float(node['size'])/.05))
        keys={(x+i,y+j) for i in range(width) for j in range(width)}
        assert not occupied.intersection(keys)
        occupied.update(keys)

def test_variance_split_and_homogeneous_sibling_merge():
    x,y=np.meshgrid(np.arange(70.01,70.49,.04),np.arange(1.01,1.49,.04))
    p=np.column_stack((x.ravel(),y.ravel(),np.zeros(x.size)))
    cls=np.zeros(len(p),np.uint8)
    tree=NdTree()
    first=tree.build(p,cls)
    assert len(first.nodes)==1
    varied=p.copy();varied[::2,2]=.5
    split=tree.build(varied,cls)
    assert len(split.nodes)>len(first.nodes)
    merged=tree.build(p,cls)
    assert len(merged.nodes)==1
    assert merged.nodes['point_count'][0]==len(p)

def test_elevation_unknown_empty_and_out_of_range():
    p=np.array([[1.001,1.001,-1],[1.002,1.002,2],[101,0,0],[np.nan,0,0]])
    r=NdTree().build(p,np.array([2,2,3,0],np.uint8))
    assert len(r.nodes)==1
    assert r.nodes['min_z'][0]==-1 and r.nodes['max_z'][0]==2
    assert r.nodes['mean_z'][0]==.5
    assert r.point_classes.tolist()==[2,2,255,255]
    assert len(NdTree().build(np.empty((0,3)),np.array([],np.uint8)).nodes)==0

def test_confidence_validation():
    with pytest.raises(ValueError): NdTree().build([[0,0,0]],[1],[1.1])

def test_distance_and_ground_are_distinct_when_heights_vary():
    rng=np.random.default_rng(9)
    p=np.column_stack((rng.uniform(70,71,1000),rng.uniform(0,1,1000),rng.uniform(0,1,1000)))
    cls=np.full(len(p),2,np.uint8)
    assert len(NdTree('ground').build(p,cls).nodes)>len(NdTree('distance').build(p,cls).nodes)
