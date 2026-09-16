from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_api_main() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")

    import_line = (
        "from app.confirmed_generation_routes import "
        "router as confirmed_generation_router"
    )
    if import_line not in text:
        lines = text.splitlines()
        insert_at = 0
        while insert_at < len(lines) and (
            lines[insert_at].startswith("from __future__")
            or not lines[insert_at].strip()
        ):
            insert_at += 1
        lines.insert(insert_at, import_line)
        text = "\n".join(lines) + "\n"

    include_line = "app.include_router(confirmed_generation_router)"
    if include_line not in text:
        text = text.rstrip() + "\n\n" + include_line + "\n"

    path.write_text(text, encoding="utf-8")


def patch_package_json() -> None:
    path = ROOT / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.setdefault("scripts", {})

    scripts["confirmed-generation:check"] = (
        "python scripts/check-confirmed-generation-binding.py"
    )
    scripts["phase24:contracts"] = (
        "python scripts/inspect-phase24-final-contracts.py"
    )

    validate = scripts.get("validate")
    if not isinstance(validate, str):
        raise SystemExit("Root package.json has no validate script.")

    marker = "pnpm requirements:check"
    if "pnpm confirmed-generation:check" not in validate:
        if marker in validate:
            validate = validate.replace(
                marker,
                marker + " && pnpm confirmed-generation:check",
                1,
            )
        else:
            validate = "pnpm confirmed-generation:check && " + validate

    scripts["validate"] = validate
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


patch_api_main()
patch_package_json()

print("Phase 24B confirmed-requirements generation binding integrated.")
