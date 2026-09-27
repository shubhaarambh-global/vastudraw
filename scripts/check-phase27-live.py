from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

print("1/2 Qualifying the current hybrid provider stack through runtime factories...")
subprocess.run(
    [sys.executable, str(ROOT / "scripts/check-phase29c-live.py")],
    cwd=ROOT,
    check=True,
)

print("2/2 Running the existing fail-closed production launch gate...")
subprocess.run(
    [sys.executable, str(ROOT / "scripts/check-production-launch.py")],
    cwd=ROOT,
    check=True,
)

print(
    "PHASE27_LIVE_PREFLIGHT PASS: providers_live=true, launch_checks=true, "
    "production_qualification=false"
)
