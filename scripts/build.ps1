# Build the frontend into frontend/dist (single-port deploy).
# ASCII-only on purpose: Windows PowerShell 5.1 reads BOM-less scripts as ANSI.
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root 'frontend'
Set-Location -LiteralPath $frontend

if (-not (Test-Path -LiteralPath 'node_modules')) {
    Write-Host '[*] Installing frontend dependencies ...'
    npm install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { Write-Host '[!] npm install failed.'; exit 1 }
}

Write-Host '[*] Building frontend ...'
npm run build
if ($LASTEXITCODE -ne 0) { Write-Host '[!] Build failed.'; exit 1 }

$dist = Join-Path $frontend 'dist'
Write-Host "[ok] Build finished: $dist"
Get-ChildItem -LiteralPath (Join-Path $dist 'assets') -File |
    Select-Object Name, @{n = 'KB'; e = { [math]::Round($_.Length / 1KB, 1) } } |
    Format-Table -AutoSize
