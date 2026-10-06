param(
    [ValidateSet('vastu', 'generation', 'remainder', 'uploads', 'persistence', 'unavailable', 'revision', 'basic', 'negative_uploads', 'text_requirements', 'billing_limits')]
    [string]$AcceptanceMode
)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if ($env:AI_VASTU_DATABASE_URL) { throw 'Phase 29F requires local SQLite; database URL must be unset.' }
$env:APP_ENV = 'development'
$env:AI_VASTU_AUTH_MODE = 'development'
$env:AI_VASTU_DEV_BEARER_TOKEN = 'dev-local-token'
$env:AI_VASTU_DEV_USER_ID = '11111111-1111-1111-1111-111111111111'
$env:AI_VASTU_SQLITE_PATH = '.local/phase29f-projects.sqlite3'
$env:AI_VASTU_BILLING_SQLITE_PATH = '.local/phase29f-billing.sqlite3'
$env:AI_VASTU_REQUIREMENTS_PATH = '.local/phase29f-requirements'
$env:AI_VASTU_GENERATION_UPLOAD_ROOT = '.local/phase29f-generation-intakes'
$env:AI_VASTU_PAYMENT_GATEWAY = 'disabled'
$env:AI_VASTU_DEV_BILLING_BYPASS = '1'
foreach ($selector in @('REQUIREMENTS', 'ARCHITECT', 'VASTU', 'ARCHITECTURAL_BRAIN', 'REVISION', 'PLAN_RECOGNITION')) {
    [Environment]::SetEnvironmentVariable("AI_VASTU_${selector}_PROVIDER", 'ollama_local', 'Process')
}
$env:AI_VASTU_OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:AI_VASTU_OLLAMA_MODEL = 'qwen3-vl:8b-instruct-q4_K_M'
$env:AI_VASTU_OLLAMA_CONNECT_TIMEOUT_SECONDS = '3'
$env:AI_VASTU_OLLAMA_READ_TIMEOUT_SECONDS = '300'
$env:AI_VASTU_OLLAMA_TOTAL_TIMEOUT_SECONDS = '360'
$env:AI_VASTU_OLLAMA_WRITE_TIMEOUT_SECONDS = '30'
$env:AI_VASTU_OLLAMA_POOL_TIMEOUT_SECONDS = '3'
$env:PYTHONPATH = 'python;apps/api'
if ($AcceptanceMode) {
    if ($AcceptanceMode -eq 'billing_limits') {
        & .\.venv\Scripts\python.exe -u scripts/phase29f-billing-acceptance.py
        exit $LASTEXITCODE
    }
    & .\.venv\Scripts\python.exe -u scripts/phase29f-local-acceptance.py $AcceptanceMode
    exit $LASTEXITCODE
}
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
