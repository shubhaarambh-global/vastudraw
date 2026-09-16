$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path .venv)) { throw ".venv not found. Run .\scripts\bootstrap-windows.ps1 first." }
& .\.venv\Scripts\Activate.ps1
ruff check python apps/api tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
mypy
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
pnpm validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "PHASE 7 ACCEPTANCE GATE: PASS"
