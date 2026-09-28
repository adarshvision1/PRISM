"""Architecture identity and artifact locations; legacy PointNet++ paths stay valid."""
from dataclasses import dataclass
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ModelSpec:
    key: str
    title: str
    weights: Path
    log: Path
    run: Path
    export_dir: Path

    @property
    def checkpoint(self):
        if self.key == 'pointnet2':
            return ROOT / json.loads((ROOT / 'config.json').read_text())['checkpoint']
        return self.weights / 'best.ckpt'

    @property
    def bundle(self):
        return self.export_dir / 'PRISM-trained-model.zip'


MODELS = {
    'pointnet2': ModelSpec('pointnet2', 'PointNet++ MSG', ROOT/'backend/model/weights',
                         ROOT/'docs/training_log.csv', ROOT/'data/training_run.json', ROOT/'data/deployment'),
    'pointnext_s': ModelSpec('pointnext_s', 'PointNeXt-S · outdoor adaptation', ROOT/'backend/model/weights/pointnext_s',
                           ROOT/'data/models/pointnext_s/training.csv', ROOT/'data/models/pointnext_s/training_run.json',
                           ROOT/'data/deployment/pointnext_s'),
}


def get_spec(key):
    if key not in MODELS:
        raise ValueError('Choose pointnet2 or pointnext_s')
    return MODELS[key]


def build_model(architecture='pointnet2', **config):
    get_spec(architecture)
    if architecture == 'pointnext_s':
        from .pointnext.network import PointNeXtSmall
        return PointNeXtSmall(**config)
    from .pointnet2.network import PointNet2MSG
    return PointNet2MSG(**config)


def checkpoint_architecture(checkpoint):
    return checkpoint.get('architecture', 'pointnet2')
