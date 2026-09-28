"""Checkpoint-aware model catalog, downloads and comparison evidence."""
import hashlib
import json
from functools import lru_cache
from backend.model.registry import MODELS, ROOT, get_spec, checkpoint_architecture


@lru_cache(maxsize=8)
def checkpoint_info(path, modified, size):
    import torch
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    return {'architecture': checkpoint_architecture(checkpoint),
            'trained': checkpoint.get('status', '').startswith('trained'),
            'epoch': checkpoint.get('epoch'), 'validation_miou': checkpoint.get('val_miou'),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def describe(key):
    spec = get_spec(key)
    result = {'id': key, 'name': spec.title, 'ready': False, 'download_ready': False,
              'status': 'Needs training', 'validation_miou': None}
    if spec.checkpoint.exists():
        stat = spec.checkpoint.stat()
        try:
            info = checkpoint_info(spec.checkpoint, stat.st_mtime_ns, stat.st_size)
            result.update(info)
            result['ready'] = info['trained'] and info['architecture'] == key
            result['status'] = 'Ready to process' if result['ready'] else 'Needs training'
        except (OSError, ValueError, RuntimeError, EOFError):
            result['status'] = 'Checkpoint could not be loaded'
    manifest = spec.export_dir / 'manifest.json'
    if result['ready'] and spec.bundle.exists() and manifest.exists():
        try:
            metadata = json.loads(manifest.read_text())['checkpoint']
            result['download_ready'] = metadata['sha256'] == result['sha256']
        except (KeyError, ValueError, OSError):
            pass
    result['download_url'] = f'/api/models/{key}/download' if result['download_ready'] else None
    return result


def catalog():
    models = [describe(key) for key in MODELS]
    path = ROOT / 'data/model_comparison.json'
    comparison = json.loads(path.read_text()) if path.exists() else None
    if comparison:
        hashes = {m['id']: m.get('sha256') for m in models}
        comparison['current'] = all(hashes.get(row['architecture']) == row['checkpoint_sha256'] for row in comparison['models'])
    return {'models': models, 'comparison': comparison}


def require_ready(key):
    status = describe(key)
    if not status['ready']:
        raise ValueError(f"{status['name']}: {status['status']}. Train this architecture first.")
    return status
