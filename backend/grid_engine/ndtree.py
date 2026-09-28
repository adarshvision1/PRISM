"""Sparse, disjoint 2.5-D Nd-tree with a hard safety override.

Uses variable branching (2 or 5 per axis) because 5/10/25/50 cm are not
a dyadic sequence. All statistics are aggregated in NumPy, without point loops.
"""
from dataclasses import dataclass
from time import perf_counter
import numpy as np
from backend.grid_engine.split_tests import semantic_split

SAFETY_FLOOR_RADIUS_M = 3.0
MIN_CELL_M = 0.05
MAX_RANGE_M = 100.0
HEIGHT_VARIANCE_THRESHOLD = 0.025 ** 2
OCCUPANCY_VARIANCE_THRESHOLD = 0.12
TRANSITION_BAND_M = 2.0
CONFIGS = ('uniform', 'distance', 'ground', 'semantic', 'prism')
NODE_DTYPE = np.dtype([
    ('x', 'f4'), ('y', 'f4'), ('size', 'f4'),
    ('min_z', 'f4'), ('max_z', 'f4'), ('mean_z', 'f4'),
    ('point_count', 'i4'), ('dominant_class', 'u1'),
    ('class_confidence', 'f4'), ('occupancy_variance', 'f4'), ('height_variance', 'f4'),
    ('semantic_complexity', '?'),
])

def fovea_distance(xy, speed=0.0, heading=0.0):
    speed = np.clip(speed, 0, 80)
    direction = np.array([np.cos(heading), np.sin(heading)])
    shifted = xy - np.clip(0.2 * speed, 0, 5) * direction
    # Two scalar components avoid dispatching small 2D vectors through BLAS.
    along = shifted[:,0]*direction[0]+shifted[:,1]*direction[1]
    across = -shifted[:,0]*direction[1]+shifted[:,1]*direction[0]
    return np.hypot(along / min(1 + 0.033 * speed, 2), across)

def resolution_ceiling(xy, speed=0.0, heading=0.0, fovea=True):
    distance = fovea_distance(xy, speed, heading) if fovea else np.linalg.norm(xy, axis=1)
    return np.select([distance < 10, distance < 25, distance < 60], [.05, .1, .25], .5)

def _hash(x, y):
    # Stable spatial dither: the same region does not flicker between frames.
    return np.mod(np.sin(x * 12.9898 + y * 78.233) * 43758.5453, 1.0)

def _region_ceiling(origins, size, speed, heading, fovea, safety):
    # Conservative lower bound to elliptical distance over the ENTIRE cell.
    center = origins + size / 2
    near = np.maximum(0, (fovea_distance(center, speed, heading) if fovea else np.linalg.norm(center, axis=1)) - size / np.sqrt(2))
    ceiling = np.select([near < 10, near < 25, near < 60], [.05, .1, .25], .5)
    # Blend on the COARSER side only, thus never violating the hard ceiling.
    h = _hash(origins[:, 0], origins[:, 1])
    for boundary, fine in ((10, .05), (25, .1), (60, .25)):
        blend = (near >= boundary) & (near < boundary + TRANSITION_BAND_M)
        ceiling[blend & (h < 1 - (near-boundary)/TRANSITION_BAND_M)] = fine
    if safety:
        closest = np.maximum(np.maximum(origins, -(origins + size)), 0)
        ceiling[np.linalg.norm(closest, axis=1) <= SAFETY_FLOOR_RADIUS_M] = MIN_CELL_M
    return ceiling

def _aggregate(points, classes, confidence, indices, size):
    coord = np.floor(points[indices, :2] / size + 1e-7).astype(np.int32)
    # A scalar key avoids costly axis-wise np.unique; valid range is +/-100 m.
    keys = (coord[:, 0].astype(np.int64) + 4096) * 8192 + coord[:, 1] + 4096
    unique, inverse = np.unique(keys, return_inverse=True)
    count = np.bincount(inverse)
    z = points[indices, 2]
    mean = np.bincount(inverse, weights=z) / count
    variance = np.maximum(0, np.bincount(inverse, weights=z*z) / count - mean*mean)
    zmin = np.full(len(unique), np.inf)
    zmax = np.full(len(unique), -np.inf)
    np.minimum.at(zmin, inverse, z)
    np.maximum.at(zmax, inverse, z)
    c = classes[indices]
    valid = c < 4
    votes = np.bincount(inverse[valid]*4+c[valid], weights=confidence[indices][valid], minlength=len(unique)*4).reshape(-1, 4)
    class_counts=np.bincount(inverse[valid]*4+c[valid],minlength=len(unique)*4).reshape(-1,4)
    dominant = votes.argmax(1).astype(np.uint8)
    dominant[votes.sum(1) == 0] = 255
    certainty = votes.max(1) / count
    occupied = ((c == 2) | (c == 3)).astype(float)
    occ_mean = np.bincount(inverse, weights=occupied) / count
    occ_variance = occ_mean * (1 - occ_mean)
    origins = np.column_stack((unique // 8192 - 4096, unique % 8192 - 4096)) * size
    nodes = np.zeros(len(unique), NODE_DTYPE)
    nodes['semantic_complexity']=semantic_split(class_counts)
    nodes['x'], nodes['y'], nodes['size'] = origins[:, 0], origins[:, 1], size
    for name, value in [('min_z', zmin), ('max_z', zmax), ('mean_z', mean), ('point_count', count), ('dominant_class', dominant), ('class_confidence', certainty), ('occupancy_variance', occ_variance), ('height_variance', variance)]:
        nodes[name] = value
    return nodes, inverse, origins

@dataclass
class GridResult:
    nodes: np.ndarray
    point_classes: np.ndarray
    point_cells: np.ndarray
    elapsed_ms: float
    input_points: int
    valid_points: int
    refined_nodes: int

    @property
    def memory_mb(self): return self.nodes.nbytes / 1024**2

    def wire(self, max_cells=None):
        n = self.nodes
        # Full cell set by default. Optional rendering cap never affects metrics.
        if max_cells and len(n) > max_cells: n = n[np.linspace(0, len(n)-1, max_cells, dtype=int)]
        return np.column_stack((n['x'], n['y'], n['size'], n['dominant_class'], n['mean_z'], n['class_confidence'])).round(4).tolist()

class NdTree:
    """Frame-local refit: accept homogeneous parents = merge, else subdivide.

    A refit deliberately avoids fusing moving objects across sensor poses.
    Unknown/unobserved cells are absent, never interpreted as free space.
    """
    def __init__(self, mode='prism'):
        if mode not in CONFIGS: raise ValueError(f'Unknown grid mode: {mode}')
        self.mode = mode
        self.last = None

    def build(self, points, classes, confidence=None, speed=0.0, heading=0.0):
        start = perf_counter()
        points = np.asarray(points, dtype=np.float64)
        classes = np.asarray(classes, dtype=np.uint8)
        if points.ndim != 2 or points.shape[1] < 3 or len(classes) != len(points): raise ValueError('Expected N x 3+ points and N classes')
        confidence = np.ones(len(points)) if confidence is None else np.asarray(confidence, dtype=float)
        if confidence.shape != (len(points),) or not np.isfinite(confidence).all() or np.any((confidence < 0) | (confidence > 1)): raise ValueError('Invalid confidence')
        if not np.isfinite([speed, heading]).all(): raise ValueError('Invalid motion')
        if np.any((classes > 3) & (classes != 255)): raise ValueError('Invalid macro-class')
        valid = np.isfinite(points[:, :3]).all(1) & (np.linalg.norm(points[:, :2], axis=1) < MAX_RANGE_M)
        indices = np.flatnonzero(valid)
        output = np.full(len(points), 255, np.uint8)
        point_cells = np.full(len(points), -1, np.int32)
        pending = [(indices, .05 if self.mode == 'uniform' else .5)]
        leaves, offset, refinements = [], 0, 0
        while pending:
            inds, size = pending.pop()
            if len(inds) == 0: continue
            nodes, inv, origins = _aggregate(points, classes, confidence, inds, size)
            if size <= .050001:
                split = np.zeros(len(nodes), bool)
                ceiling = np.full(len(nodes), .05)
            else:
                ceiling = _region_ceiling(origins, size, speed, heading, self.mode == 'prism', self.mode in ('ground', 'prism'))
                complex_cell = np.zeros(len(nodes), bool)
                if self.mode in ('ground', 'prism'):complex_cell |= nodes['height_variance'] > HEIGHT_VARIANCE_THRESHOLD
                if self.mode in ('semantic', 'prism'):complex_cell |= nodes['semantic_complexity']
                split = (size > ceiling + 1e-6) | complex_cell
            keep = ~split
            kept_points = keep[inv]
            lookup = np.cumsum(keep)-1
            point_cells[inds[kept_points]] = offset + lookup[inv[kept_points]]
            output[inds[kept_points]] = nodes['dominant_class'][inv[kept_points]]
            leaves.append(nodes[keep])
            offset += int(keep.sum())
            refinements += int(split.sum())
            if split.any():
                if size == .5:
                    # N=5 where 10 cm or finer is necessary; N=2 elsewhere.
                    use_tenth = split & (ceiling <= .100001)
                    pending.append((inds[use_tenth[inv]], .1))
                    pending.append((inds[(split & ~use_tenth)[inv]], .25))
                else:
                    pending.append((inds[split[inv]], .05))
        merged = np.concatenate(leaves) if leaves else np.empty(0, NODE_DTYPE)
        result = GridResult(merged, output, point_cells, (perf_counter()-start)*1000, len(points), len(indices), refinements)
        self.last = result
        return result
