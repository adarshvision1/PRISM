param(
    [ValidateSet('pointnet2', 'pointnext_s')][string]$Architecture = 'pointnext_s',
    [ValidateRange(1, 180)][int]$Minutes = 30
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$PrismPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$Checkpoint = if ($Architecture -eq 'pointnet2') { 'backend/model/weights/best.ckpt' } else { 'backend/model/weights/pointnext_s/best.ckpt' }
$TrainingArguments = @('-m', 'backend.model.train', '--architecture', $Architecture, '--minutes', "$Minutes", '--epochs', '1000', '--patience', '1000', '--cache-dir', 'data/blocks_cache_expanded')
if (Test-Path -LiteralPath $Checkpoint) { $TrainingArguments += @('--resume', '--lr', '0.0001') }
else { $TrainingArguments += @('--lr', '0.001') }
Write-Host "Training $Architecture for a $Minutes-minute budget. Best validation weights are retained."
& $PrismPython @TrainingArguments
exit $LASTEXITCODE
