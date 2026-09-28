import numpy as np
from backend.planning.occupancy import occupancy_grid
from backend.localization.odometry import motion
from backend.application.scene_service import voxel_reference

def test_costmap_unknown_and_geometric_stop_even_if_semantics_wrong():
    points=np.array([[4,0,0,1],[4.1,0,1,1],[2,2,0,1]],np.float32)
    result=occupancy_grid(points,np.zeros(3,np.uint8))
    assert result['operator_status']=='STOP'
    assert result['counts']['unknown']>0 and result['counts']['occupied']>=1
    assert result['type']=='nav_msgs/msg/OccupancyGrid'

def test_real_odometry():
    speed,heading=motion('08',1)
    assert 0<speed<50 and np.isfinite(heading)

def test_voxel_same_domain_and_boundary_exclusion():
    p=np.array([[0,0,0,1],[0,0,.049,1],[10,0,0,1],[0,0,1,1]],np.float32)
    result=voxel_reference(p)
    assert result['point_count']==2 and result['occupied']==1
    assert result['bytes']==400*400*80 and result['grid_ms']>0
