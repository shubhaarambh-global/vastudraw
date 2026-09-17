from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "phase26b5_payload"

REQUIRED_BASELINE = (
    ROOT / "apps/api/app/main.py",
    ROOT / "apps/web/src/api/client.ts",
    ROOT / "apps/web/src/components/generation/GenerationWorkspacePage.tsx",
    ROOT / "python/ai_vastu/generation_intake/models.py",
    ROOT / "python/ai_vastu/generation_intake/store.py",
    ROOT / "python/ai_vastu/vastu_reasoning/models.py",
    ROOT / "python/ai_vastu/gemini_http.py",
)

missing = [path for path in REQUIRED_BASELINE if not path.exists()]
if missing:
    joined = "\n".join(f"- {path.relative_to(ROOT)}" for path in missing)
    raise SystemExit("Phase 26B.5 baseline is incomplete. Missing:\n" + joined)

if not PAYLOAD.is_dir():
    raise SystemExit(f"Phase 26B.5 payload directory is missing: {PAYLOAD}")

copied: list[str] = []
for source in sorted(PAYLOAD.rglob("*")):
    if not source.is_file():
        continue
    relative = source.relative_to(PAYLOAD)
    destination = ROOT / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    copied.append(str(relative))

print(f"Phase 26B.5 applied: {len(copied)} files.")
for item in copied:
    print(f"  {item}")
