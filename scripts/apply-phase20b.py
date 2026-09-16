from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package.json"

payload = json.loads(PACKAGE.read_text(encoding="utf-8"))
scripts = payload.setdefault("scripts", {})

scripts["vastu:approve"] = "python scripts/record-vastu-expert-approval.py"
scripts["vastu:freeze"] = "python scripts/freeze-vastu-spec.py"
scripts["vastu:production"] = "python scripts/check-vastu-production-release.py"

validate = scripts.get("validate")
if not isinstance(validate, str):
    raise SystemExit("package.json is missing the validate script.")

needle = "pnpm vastu:check && pnpm vastu:review &&"
replacement = "pnpm vastu:check && pnpm vastu:review && pnpm vastu:production &&"
if replacement not in validate:
    if needle not in validate:
        raise SystemExit("Could not locate Phase 20 Vastu validation sequence.")
    validate = validate.replace(needle, replacement, 1)

scripts["validate"] = validate
PACKAGE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("Phase 20B package scripts integrated.")
