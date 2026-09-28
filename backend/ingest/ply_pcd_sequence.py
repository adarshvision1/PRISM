from pathlib import Path
import numpy as np
from backend.labels import read_scan
def load_points(path):
    path=Path(path)
    if path.suffix.lower()=='.bin':points=read_scan(path)
    else:
        import open3d as o3d
        cloud=o3d.t.io.read_point_cloud(str(path))
        xyz=cloud.point.positions.numpy().astype(np.float32)
        intensity=np.zeros(len(xyz),np.float32)
        if 'intensity' in cloud.point:intensity=cloud.point.intensity.numpy().reshape(-1).astype(np.float32)
        points=np.c_[xyz,intensity]
    if len(points)==0 or len(points)>2_000_000:raise ValueError('Frame must contain 1 to 2,000,000 points')
    if not np.isfinite(points).all():raise ValueError('Frame contains non-finite values')
    return points
