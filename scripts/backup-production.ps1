param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($env:AI_VASTU_DATABASE_URL)) {
    throw "AI_VASTU_DATABASE_URL is required."
}

function Resolve-BackupDirectory([string]$ConfiguredPath, [string]$SettingName) {
    if ([string]::IsNullOrWhiteSpace($ConfiguredPath)) {
        throw "$SettingName is required."
    }
    $pathRoot = [System.IO.Path]::GetPathRoot($ConfiguredPath)
    if ([string]::IsNullOrEmpty($pathRoot) -or
        -not $pathRoot.EndsWith([string][System.IO.Path]::DirectorySeparatorChar)) {
        throw "$SettingName must be an absolute path."
    }
    if ([System.IO.Path]::DirectorySeparatorChar -eq [char]'\' -and $pathRoot -eq '\') {
        throw "$SettingName must be a fully qualified path with a drive or UNC share."
    }
    if (-not (Test-Path -LiteralPath $ConfiguredPath -PathType Container)) {
        throw "$SettingName directory does not exist: $ConfiguredPath"
    }
    $resolved = (Resolve-Path -LiteralPath $ConfiguredPath).Path
    $resolvedRoot = [System.IO.Path]::GetPathRoot($resolved)
    if ($resolved.Length -eq $resolvedRoot.Length) {
        throw "$SettingName must not be a filesystem root."
    }
    if ($resolved.Length -gt $resolvedRoot.Length) {
        return $resolved.TrimEnd([System.IO.Path]::DirectorySeparatorChar)
    }
    return $resolved
}

$requirementsPath = Resolve-BackupDirectory `
    $env:AI_VASTU_REQUIREMENTS_PATH "AI_VASTU_REQUIREMENTS_PATH"
$uploadPath = Resolve-BackupDirectory `
    $env:AI_VASTU_GENERATION_UPLOAD_ROOT "AI_VASTU_GENERATION_UPLOAD_ROOT"
$outputPath = Resolve-BackupDirectory $OutputDirectory "OutputDirectory"

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $outputPath "ai-vastu-$stamp-$([guid]::NewGuid().ToString('N'))"
foreach ($source in @($requirementsPath, $uploadPath)) {
    if ($target.Equals($source, [System.StringComparison]::OrdinalIgnoreCase) -or
        $target.StartsWith(
            "$source$([System.IO.Path]::DirectorySeparatorChar)",
            [System.StringComparison]::OrdinalIgnoreCase
        )) {
        throw "Backup output must be outside persistent storage roots."
    }
}
New-Item -ItemType Directory -Path $target -ErrorAction Stop | Out-Null

$dbFile = Join-Path $target "postgres.dump"
& pg_dump `
  --format=custom `
  --no-owner `
  --no-acl `
  --file="$dbFile" `
  "$env:AI_VASTU_DATABASE_URL"

if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $dbFile -PathType Leaf)) {
    throw "pg_dump failed."
}

$requirementsArchive = Join-Path $target "requirements.tar.gz"
& tar -czf $requirementsArchive `
  -C $requirementsPath .

if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $requirementsArchive -PathType Leaf)) {
    throw "Requirements archive failed."
}

$uploadArchive = Join-Path $target "generation-uploads.tar.gz"
& tar -czf $uploadArchive `
  -C $uploadPath .

if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $uploadArchive -PathType Leaf)) {
    throw "Generation upload archive failed."
}

Get-FileHash -LiteralPath $dbFile, $requirementsArchive, $uploadArchive -Algorithm SHA256 |
    Format-Table -AutoSize

Write-Host "Backup created: $target"
