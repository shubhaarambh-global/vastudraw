param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

if (-not $env:DATABASE_URL) {
    throw "DATABASE_URL is required."
}
if (-not $env:AI_VASTU_REQUIREMENTS_PATH) {
    throw "AI_VASTU_REQUIREMENTS_PATH is required."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $OutputDirectory "ai-vastu-$stamp"
New-Item -ItemType Directory -Force -Path $target | Out-Null

$dbFile = Join-Path $target "postgres.dump"
& pg_dump `
  --format=custom `
  --no-owner `
  --no-acl `
  --file="$dbFile" `
  "$env:DATABASE_URL"

if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed."
}

$requirementsPath = [System.IO.Path]::GetFullPath(
    $env:AI_VASTU_REQUIREMENTS_PATH
)
if (-not (Test-Path $requirementsPath)) {
    throw "Requirements path does not exist: $requirementsPath"
}

tar -czf (Join-Path $target "requirements.tar.gz") `
  -C $requirementsPath .

if ($LASTEXITCODE -ne 0) {
    throw "Requirements archive failed."
}

Get-FileHash (Join-Path $target "*") -Algorithm SHA256 |
    Format-Table -AutoSize

Write-Host "Backup created: $target"
