from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_api_main() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")

    marker = "from ai_vastu.production.middleware import ProductionHardeningMiddleware"
    if marker not in text:
        text = text.rstrip() + (
            "\n\n"
            "# Phase 25 production defense-in-depth middleware.\n"
            "from ai_vastu.production.middleware import ProductionHardeningMiddleware\n\n"
            "app.add_middleware(ProductionHardeningMiddleware)\n"
        )
        path.write_text(text, encoding="utf-8")


def patch_package_json() -> None:
    path = ROOT / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.setdefault("scripts", {})

    scripts["phase25:check"] = "python scripts/check-phase25.py"
    scripts["phase25:launch"] = "python scripts/check-production-launch.py"
    scripts["licenses:audit"] = "python scripts/audit-third-party.py"

    validate = scripts.get("validate")
    if not isinstance(validate, str):
        raise SystemExit("Root package.json has no validate script.")

    if "pnpm phase25:check" not in validate:
        marker = "pnpm phase24:check"
        if marker in validate:
            validate = validate.replace(
                marker,
                marker + " && pnpm phase25:check",
                1,
            )
        else:
            validate = "pnpm phase25:check && " + validate
    scripts["validate"] = validate

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


patch_api_main()
patch_package_json()
print("Phase 25 production hardening integrated.")
