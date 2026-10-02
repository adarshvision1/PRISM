# Run PRISM locally

## Requirements

- Python and a compatible PyTorch build for your CPU or CUDA device.
- Project dependencies from [`requirements-model.txt`](../requirements-model.txt). Training and evaluation checks also use [`requirements-dev.txt`](../requirements-dev.txt).
- Available disk space for the chosen scans. The full SemanticKITTI dataset is distributed separately by its maintainers.

The Windows launcher expects `.venv` at the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-model.txt
.\start.ps1
```

Use the PyTorch installation instructions appropriate for your hardware before installing project dependencies if you need a particular CUDA build. The server preflight checks required files and the selected checkpoint. Open **http://127.0.0.1:8000/README** after startup.

The repository includes saved demonstration frames and selected model checkpoints. Full SemanticKITTI presets, retraining and labelled evaluation need the official dataset placed under `data/dataset/` as described in the [technical guide](technical-guide.md#run-the-prototype). That dataset is not committed here.

## Run checks

```powershell
.\.venv\Scripts\python.exe scripts/doctor.py
.\.venv\Scripts\python.exe -m pytest -q
```

## Compare or export models

```powershell
.\.venv\Scripts\python.exe scripts/compare_models.py --frames 32
.\.venv\Scripts\python.exe scripts/export_deployment.py --architecture all
```

The comparison requires the corresponding validation scans. Exports are generated locally under `data/deployment/`; they are not committed to Git. A TorchScript bundle is a model handoff for a compatible PyTorch runtime, not a complete scan-to-map application.

## Training

Training also requires the prepared block cache made from official SemanticKITTI scans. The scripts resume from existing checkpoints when appropriate:

```powershell
.\train.ps1 -Architecture pointnet2 -Minutes 30
.\train.ps1 -Architecture pointnext_s -Minutes 30
```

Time-bounded runs do not imply convergence. Always report the retained checkpoint epoch and validation scope.
