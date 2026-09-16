from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package.json"

payload = json.loads(PACKAGE.read_text(encoding="utf-8"))
scripts = payload.setdefault("scripts", {})

scripts["vastu:packets"] = "python scripts/export-vastu-review-packets.py"
scripts["vastu:review"] = "python scripts/check-vastu-review-candidates.py"

validate = scripts.get("validate")
if not isinstance(validate, str):
    raise SystemExit("package.json is missing the validate script.")

needle = "pnpm vastu:check &&"
replacement = "pnpm vastu:check && pnpm vastu:review &&"

if replacement not in validate:
    if needle not in validate:
        raise SystemExit("Could not locate vastu:check in validate script.")
    validate = validate.replace(needle, replacement, 1)

scripts["validate"] = validate
PACKAGE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("Phase 20 package scripts integrated.")
