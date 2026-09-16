$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 24+ is required." }
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) { throw "pnpm is required." }
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python 3.12+ is required." }

if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pnpm install
pnpm contracts:generate
Write-Host "Bootstrap complete. Run: .\scripts\validate-windows.ps1"
