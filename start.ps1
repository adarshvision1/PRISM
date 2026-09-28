param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$PrismPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $PrismPython)) {
    Write-Host 'Local Python environment missing. See README.md for installation.'
    exit 1
}
& $PrismPython scripts/doctor.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "PRISM: http://127.0.0.1:$Port/README"
Write-Host 'Everything runs locally. Keep this window open.'
& $PrismPython -m uvicorn backend.api.server:app --host 127.0.0.1 --port $Port
