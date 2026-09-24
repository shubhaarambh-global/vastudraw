from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "backup-production.ps1"
RUNBOOK = ROOT / "docs" / "runbooks" / "backup-restore.md"


def test_backup_uses_canonical_database_url_and_archives_both_persistent_roots() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "$env:AI_VASTU_DATABASE_URL" in script
    assert "$env:DATABASE_URL" not in script
    assert "Resolve-BackupDirectory `\n    $env:AI_VASTU_REQUIREMENTS_PATH" in script
    assert "Resolve-BackupDirectory `\n    $env:AI_VASTU_GENERATION_UPLOAD_ROOT" in script
    assert '"requirements.tar.gz"' in script
    assert '"generation-uploads.tar.gz"' in script
    assert script.count("& tar -czf") == 2
    assert "-C $requirementsPath ." in script
    assert "-C $uploadPath ." in script
    assert "Get-FileHash -LiteralPath $dbFile, $requirementsArchive, $uploadArchive" in script


def test_backup_validates_inputs_and_each_artifact_before_reporting_success() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    assert "GetPathRoot($ConfiguredPath)" in script
    assert "must be a fully qualified path with a drive or UNC share" in script
    assert 'throw "$SettingName must not be a filesystem root."' in script
    assert "Test-Path -LiteralPath $ConfiguredPath -PathType Container" in script
    assert 'Resolve-BackupDirectory $OutputDirectory "OutputDirectory"' in script
    assert "Backup output must be outside persistent storage roots" in script
    assert script.count("$LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath") == 3
    assert script.index("Generation upload archive failed") < script.index("Backup created:")

    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "AI_VASTU_DATABASE_URL" in runbook
    assert "AI_VASTU_REQUIREMENTS_PATH" in runbook
    assert "AI_VASTU_GENERATION_UPLOAD_ROOT" in runbook
    assert "generation-uploads.tar.gz" in runbook


@pytest.mark.skipif(shutil.which("powershell") is None, reason="Windows PowerShell is unavailable")
def test_backup_rejects_filesystem_root_as_persistent_storage() -> None:
    drive_root = Path.cwd().anchor
    environment = os.environ.copy()
    environment.update(
        {
            "AI_VASTU_DATABASE_URL": "postgresql://unused.invalid/database",
            "AI_VASTU_REQUIREMENTS_PATH": drive_root,
            "AI_VASTU_GENERATION_UPLOAD_ROOT": drive_root,
        }
    )
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-OutputDirectory",
            drive_root,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert completed.returncode != 0
    assert "must not be a filesystem root" in (completed.stderr + completed.stdout)


@pytest.mark.skipif(shutil.which("powershell") is None, reason="Windows PowerShell is unavailable")
def test_backup_rejects_windows_rooted_drive_relative_storage_path() -> None:
    rooted_without_drive = str(Path.cwd())[2:]
    assert rooted_without_drive.startswith("\\")
    environment = os.environ.copy()
    environment.update(
        {
            "AI_VASTU_DATABASE_URL": "postgresql://unused.invalid/database",
            "AI_VASTU_REQUIREMENTS_PATH": rooted_without_drive,
            "AI_VASTU_GENERATION_UPLOAD_ROOT": rooted_without_drive,
        }
    )
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-OutputDirectory",
            rooted_without_drive,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert completed.returncode != 0
    assert "must be a fully qualified path" in (completed.stderr + completed.stdout)


@pytest.mark.skipif(shutil.which("powershell") is None, reason="Windows PowerShell is unavailable")
def test_backup_archives_both_roots_with_offline_tool_stubs(tmp_path: Path) -> None:
    requirements = tmp_path / "requirements"
    uploads = tmp_path / "uploads"
    output = tmp_path / "backups"
    for directory in (requirements, uploads, output):
        directory.mkdir()

    environment = os.environ.copy()
    environment.update(
        {
            "AI_VASTU_DATABASE_URL": "postgresql://unused.invalid/database",
            "AI_VASTU_REQUIREMENTS_PATH": str(requirements),
            "AI_VASTU_GENERATION_UPLOAD_ROOT": str(uploads),
            "PHASE29B_BACKUP_SCRIPT": str(SCRIPT),
            "PHASE29B_BACKUP_OUTPUT": str(output),
        }
    )
    command = r"""
function pg_dump {
    foreach ($argument in $args) {
        if ($argument -like '--file=*') {
            [System.IO.File]::WriteAllText($argument.Substring(7), 'offline database stub')
        }
    }
    $global:LASTEXITCODE = 0
}
function tar {
    [System.IO.File]::WriteAllText($args[1], [string]$args[3])
    $global:LASTEXITCODE = 0
}
& $env:PHASE29B_BACKUP_SCRIPT -OutputDirectory $env:PHASE29B_BACKUP_OUTPUT
"""
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )
    assert completed.returncode == 0, completed.stderr
    backup_directories = list(output.iterdir())
    assert len(backup_directories) == 1
    backup = backup_directories[0]
    assert (backup / "postgres.dump").read_text() == "offline database stub"
    assert (backup / "requirements.tar.gz").read_text() == str(requirements)
    assert (backup / "generation-uploads.tar.gz").read_text() == str(uploads)
