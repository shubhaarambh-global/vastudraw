from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _patch_root_package() -> None:
    path = ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = payload.setdefault("scripts", {})
    scripts["auth:check"] = "python scripts/check-auth-authorization.py"
    scripts["auth:live"] = "python scripts/check-auth-live.py"
    validate = scripts.get("validate")
    if not isinstance(validate, str):
        raise SystemExit("Root package.json does not contain a validate script.")
    if "pnpm auth:check" not in validate:
        anchor = "pnpm persistence:check && "
        if anchor not in validate:
            raise SystemExit("Could not find persistence gate in root validate script.")
        validate = validate.replace(anchor, anchor + "pnpm auth:check && ", 1)
    scripts["validate"] = validate
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _patch_web_package() -> None:
    path = ROOT / "apps/web/package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    dependencies = payload.setdefault("dependencies", {})
    dependencies["@supabase/supabase-js"] = "2.57.4"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _patch_pyproject() -> None:
    path = ROOT / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    if "PyJWT[crypto]" not in text:
        anchor = '  "Pillow==12.3.0",\n'
        if anchor not in text:
            raise SystemExit("Could not find dependency insertion anchor in pyproject.toml.")
        text = text.replace(anchor, anchor + '  "PyJWT[crypto]>=2.10,<3",\n', 1)
    path.write_text(text, encoding="utf-8")


_patch_root_package()
_patch_web_package()
_patch_pyproject()
print("Phase 19 package/dependency wiring applied.")
