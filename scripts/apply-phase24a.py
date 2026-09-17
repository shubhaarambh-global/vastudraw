from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_api_main() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")

    import_line = "from app.requirements_routes import router as requirements_router"
    if import_line not in text:
        lines = text.splitlines()
        insert_at = 0
        while insert_at < len(lines) and (
            lines[insert_at].startswith("from __future__") or not lines[insert_at].strip()
        ):
            insert_at += 1
        lines.insert(insert_at, import_line)
        text = "\n".join(lines) + "\n"

    include_line = "app.include_router(requirements_router)"
    if include_line not in text:
        text = text.rstrip() + "\n\n" + include_line + "\n"

    path.write_text(text, encoding="utf-8")


def patch_package_json() -> None:
    path = ROOT / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.setdefault("scripts", {})
    scripts["requirements:check"] = "python scripts/check-requirements-interpreter.py"
    scripts["generation:contract"] = "python scripts/inspect-generation-contract.py"

    validate = scripts.get("validate")
    if not isinstance(validate, str):
        raise SystemExit("Root package.json has no validate script.")

    marker = "pnpm generation-intake:check"
    if "pnpm requirements:check" not in validate:
        if marker in validate:
            validate = validate.replace(
                marker,
                marker + " && pnpm requirements:check",
                1,
            )
        else:
            validate = "pnpm requirements:check && " + validate
    scripts["validate"] = validate
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def patch_env_example() -> None:
    path = ROOT / ".env.example"
    if not path.exists():
        path.write_text("", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    block = """
# Phase 24A requirements interpreter
AI_VASTU_REQUIREMENTS_PROVIDER=fixture
AI_VASTU_REQUIREMENTS_PATH=.local/requirement-drafts
OPENAI_API_KEY=
AI_VASTU_OPENAI_MODEL=
""".lstrip()
    if "AI_VASTU_REQUIREMENTS_PROVIDER=" not in text:
        text = text.rstrip() + "\n\n" + block
    path.write_text(text, encoding="utf-8")


patch_api_main()
patch_package_json()
patch_env_example()

print("Phase 24A multimodal requirements interpretation integrated.")
