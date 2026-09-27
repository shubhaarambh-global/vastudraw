from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

print("Running the current hybrid provider qualification through runtime factories...")
subprocess.run(
    [sys.executable, str(ROOT / "scripts/check-phase29c-live.py")],
    cwd=ROOT,
    check=True,
)
print("PHASE 28 HYBRID AI LIVE QUALIFICATION PASSED")
