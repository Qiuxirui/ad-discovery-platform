# Development mode: backend with --reload on 8000 + vite dev server on 5173.
# Vite proxies /api and /static to 127.0.0.1:8000, so open http://127.0.0.1:5173
# ASCII-only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as ANSI.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$frontend = Join-Path $root 'frontend'

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host '[!] .venv not found. Create it first:'
    Write-Host '    python -m venv .venv'
    Write-Host '    .venv\Scripts\python -m pip install -r backend\requirements.txt'
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $root 'backend\data\adx.db'))) {
    Write-Host '[*] Seeding database ...'
    & $python -m backend.seed
}

Write-Host '[*] Backend  : http://127.0.0.1:8000 (reload) in a new window'
Start-Process -FilePath $python `
    -ArgumentList '-m', 'uvicorn', 'backend.main:app', '--reload', '--port', '8000' `
    -WorkingDirectory $root

Write-Host '[*] Frontend : http://127.0.0.1:5173 (vite dev, Ctrl+C to stop)'
Set-Location -LiteralPath $frontend
npm run dev
