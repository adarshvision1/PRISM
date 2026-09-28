"""Export one trained architecture; publish only after numerical parity checks."""
import argparse, copy, hashlib, json, os, sys, tempfile, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import torch
from backend.model.inference import SegmentationPredictor
from backend.model.registry import MODELS, get_spec


def export(architecture):
    spec = get_spec(architecture)
    predictor = SegmentationPredictor(architecture=architecture, freeze=True)
    predictor.model.float().eval()
    cpu_model = copy.deepcopy(predictor.model).float().cpu().eval()
    spec.export_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=spec.export_dir) as temporary:
        out = Path(temporary)
        checks, files = [], []
        with torch.inference_mode():
            for n in (4096, 1024):
                torch.manual_seed(53)
                model = torch.jit.trace(cpu_model, torch.randn(1, 6, n), check_trace=False, strict=False)
                path = out / f'{architecture}-{n}.torchscript.pt'
                model.save(str(path))
                for device in ['cpu'] + (['cuda'] if predictor.device.type == 'cuda' else []):
                    reference = cpu_model if device == 'cpu' else predictor.model
                    compiled = torch.jit.load(str(path), map_location=device).eval()
                    for batch in (1, 2):
                        x = torch.randn(batch, 6, n, device=device)
                        expected, actual = reference(x), compiled(x)
                        error = float((expected - actual).abs().max())
                        if not torch.allclose(expected, actual, rtol=1e-4, atol=1e-5):
                            raise RuntimeError(f'Export parity failed: {device}, N={n}, error={error}')
                        checks.append(dict(points=n, batch=batch, device=device, max_logit_error=error))
                files.append(path)
        manifest = {'architecture': architecture, 'format': 'TorchScript FP32, fixed point counts',
            'checkpoint': predictor.metadata, 'parity_checks': checks,
            'inputs': 'B x 6 x N float32: block-local x,y,z,intensity,height above ground,motion residual=0; N=4096 or 1024',
            'outputs': 'B x 4 x N logits; softmax over dimension 1',
            'scope': 'Portable PyTorch artifact; preprocessing required. No target-device FPS, TensorRT or Jetson certification.',
            'sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
        (out/'manifest.json').write_text(json.dumps(manifest, indent=2))
        (out/'MODEL_CARD.md').write_text(
            f'# {spec.title} deployment bundle\n\nCheckpoint epoch {predictor.metadata["epoch"]}. Exact checkpoint hash and parity results are in manifest.json.\n\n'
            f'Load `torch.jit.load("{architecture}-4096.torchscript.pt", map_location="cpu").eval()`. '
            'Use the 1024 variant only for that point count. Tested batch sizes: 1 and 2. '
            'Apply the included preprocessing and block reassembly before interpreting a full scan.\n\n'
            'Classes: drivable, non-drivable terrain, static obstacle, dynamic-object semantics. '
            'These are semantic classes, not measured motion. The sixth input channel is zero.\n\n'
            'TorchScript requires compatible PyTorch; it is not a standalone TensorRT engine. '
            'Measure latency and accuracy on the intended edge device before deployment.\n')
        files += [out/'manifest.json', out/'MODEL_CARD.md']
        bundle = out / spec.bundle.name
        checkpoint_bytes=spec.checkpoint.read_bytes()
        if hashlib.sha256(checkpoint_bytes).hexdigest()!=predictor.metadata['sha256']:
            raise RuntimeError('Checkpoint changed during export. Wait for training to finish, then export again.')
        with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
            for f in files:archive.write(f, f.name)
            for f in (ROOT/'backend').rglob('*.py'):archive.write(f, f.relative_to(ROOT))
            for name in ('config.json','requirements.txt','requirements-model.txt','data/semantic-kitti.yaml','vendor/semantic-kitti-LICENSE'):
                archive.write(ROOT/name, name)
            archive.writestr('weights/best.ckpt', checkpoint_bytes)
            for name in ('backend/model/pointnet2/LICENSE','backend/model/pointnext/NOTICE.md'):
                if (ROOT/name).exists():archive.write(ROOT/name, name)
        for f in files + [bundle]:os.replace(f, spec.export_dir/f.name)
    print(f'Exported {spec.title}: {spec.bundle}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--architecture', choices=[*MODELS, 'all'], default='pointnet2')
    args = parser.parse_args()
    for key in MODELS if args.architecture == 'all' else [args.architecture]:export(key)


if __name__ == '__main__':main()
