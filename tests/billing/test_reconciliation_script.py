from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_reconciliation_rejects_unknown_app_environment_before_local_state(
    tmp_path: Path,
) -> None:
    environment = dict(os.environ)
    environment["APP_ENV"] = "prod"
    environment["PYTHONPATH"] = str(ROOT / "python")

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "reconcile-phonepe-payments.py")],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout.strip() == '{"error": "invalid_app_environment"}'
    assert completed.stderr == ""
    assert not (tmp_path / ".local").exists()
