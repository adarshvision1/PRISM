from pathlib import Path
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLASS_NAMES = ('drivable', 'non-drivable-terrain', 'static-obstacle', 'dynamic-object')
UNKNOWN = 255

def config():
    return yaml.safe_load((ROOT / 'data/semantic-kitti.yaml').read_text())

def macro_lut():
    """Names are read from the downloaded official config, never guessed IDs."""
    groups = ({9,10}, {11,12,17}, {13,14,15,16,18,19}, set(range(1,9)))
    lut = np.full(65536, UNKNOWN, np.uint8)
    cfg=config()
    for raw_id, learned in cfg['learning_map'].items():
        if cfg['learning_ignore'].get(learned,True): continue
        for i, ids in enumerate(groups):
            if learned in ids: lut[raw_id]=i
        if lut[raw_id]==UNKNOWN: raise ValueError(f'Unmapped learning ID: {learned}')
    return lut

def learning_to_macro():
    lut = macro_lut()
    return np.array([lut[raw] for _, raw in sorted(config()['learning_map_inv'].items())], np.uint8)

def read_scan(path):
    values = np.fromfile(path, dtype='<f4')
    if len(values) % 4: raise ValueError('Invalid KITTI scan length')
    return values.reshape(-1, 4)

def read_truth(path):
    return macro_lut()[(np.fromfile(path, dtype='<u4') & 0xFFFF)]
