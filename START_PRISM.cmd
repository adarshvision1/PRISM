@echo off
cd /d "%~dp0"
echo Starting PRISM at http://localhost:8000
echo Open that address in your browser. Keep this window open.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
pause
