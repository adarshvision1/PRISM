$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$cache = Join-Path $PSScriptRoot 'data\blocks_cache_expanded'
$checkpoint = Join-Path $PSScriptRoot 'backend\model\weights\best.ckpt'

if (-not (Test-Path -LiteralPath $python)) { throw "Project virtual environment not found: $python" }
if (-not (Test-Path -LiteralPath $checkpoint)) { throw "Best-validation checkpoint not found: $checkpoint" }
$gpu = & $python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CUDA unavailable'); raise SystemExit(0 if torch.cuda.is_available() else 2)"
if ($LASTEXITCODE -ne 0) { throw 'CUDA is unavailable. Refusing to spend the time-box training on CPU.' }
Write-Host "Training device: $gpu"
if (-not (Test-Path -LiteralPath (Join-Path $cache 'manifest.json'))) {
    throw "Expanded block cache is missing. Run the preparation commands in README.md first."
}

$manifest = Get-Content -LiteralPath (Join-Path $cache 'manifest.json') -Raw | ConvertFrom-Json
$expectedTrain = @('00','01','02','03','04','05','06','07','09','10')
$actualTrain = @($manifest.train.sequences | Sort-Object -Unique)
if (@(Compare-Object $expectedTrain $actualTrain).Count -ne 0) {
    throw "Training cache sequence split is unexpected. Refusing to start: $($actualTrain -join ', ')"
}
if (@($manifest.valid.sequences | Where-Object { $_ -ne '08' }).Count -gt 0) {
    throw 'Validation cache contains a sequence other than held-out sequence 08. Refusing to train.'
}
if ([int]$manifest.train.blocks -lt 10000) {
    throw "Only $($manifest.train.blocks) training blocks are available; expected at least 10,000."
}

Write-Host "Training blocks: $($manifest.train.blocks) | held-out validation blocks: $($manifest.valid.blocks)"
Write-Host 'Resuming from best validation checkpoint; AMP, graceful Ctrl+C, and CUDA OOM batch probing are enabled.'
& $python -m backend.model.train --resume --cache-dir 'data/blocks_cache_expanded' --minutes 30 --epochs 1000 --patience 1000 --lr 0.0001
if ($LASTEXITCODE -ne 0) { throw "Training exited with code $LASTEXITCODE" }
