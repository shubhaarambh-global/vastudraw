from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROVIDER_SWITCHES = (
    "AI_VASTU_REQUIREMENTS_PROVIDER",
    "AI_VASTU_ARCHITECT_PROVIDER",
    "AI_VASTU_VASTU_PROVIDER",
    "AI_VASTU_PLAN_RECOGNITION_PROVIDER",
    "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
    "AI_VASTU_REVISION_PROVIDER",
)

if not os.getenv("OPENROUTER_API_KEY", "").strip():
    raise SystemExit("OPENROUTER_API_KEY is required for Phase 27 live qualification.")

wrong = [
    name
    for name in PROVIDER_SWITCHES
    if os.getenv(name, "").strip().lower() != "openrouter"
]
if wrong:
    raise SystemExit(
        "Phase 27 live qualification requires these provider switches to equal "
        "'openrouter': " + ", ".join(wrong)
    )

print("1/2 Qualifying the validated live OpenRouter stack...")
subprocess.run(
    [sys.executable, str(ROOT / "scripts/check-openrouter-live.py")],
    cwd=ROOT,
    check=True,
)

print("2/2 Running the existing fail-closed production launch gate...")
subprocess.run(
    [sys.executable, str(ROOT / "scripts/check-production-launch.py")],
    cwd=ROOT,
    check=True,
)

print("PHASE 27 LIVE V1 RELEASE QUALIFICATION PASSED")
