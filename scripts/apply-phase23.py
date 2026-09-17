from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_package_json() -> None:
    path = ROOT / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.setdefault("scripts", {})
    scripts["billing:check"] = "python scripts/check-billing-entitlements.py"

    validate = scripts.get("validate")
    if not isinstance(validate, str):
        raise SystemExit("Root package.json is missing the validate script.")

    marker = "pnpm generation-intake:check"
    if "pnpm billing:check" not in validate:
        if marker in validate:
            validate = validate.replace(
                marker,
                marker + " && pnpm billing:check",
                1,
            )
        else:
            validate = "pnpm billing:check && " + validate
    scripts["validate"] = validate
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def patch_api_main() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")

    import_line = "from app.billing_routes import router as billing_router"
    if import_line not in text:
        lines = text.splitlines()
        insert_at = 0
        while insert_at < len(lines) and (
            lines[insert_at].startswith("from __future__") or not lines[insert_at].strip()
        ):
            insert_at += 1
        lines.insert(insert_at, import_line)
        text = "\n".join(lines) + "\n"

    include_line = "app.include_router(billing_router)"
    if include_line not in text:
        if "app = FastAPI" not in text:
            raise SystemExit("Could not locate FastAPI app in apps/api/app/main.py.")
        text = text.rstrip() + "\n\n" + include_line + "\n"

    path.write_text(text, encoding="utf-8")


def patch_env_example() -> None:
    path = ROOT / ".env.example"
    if not path.exists():
        path.write_text("", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    block = """
# Phase 23 billing
AI_VASTU_BILLING_SQLITE_PATH=.local/billing.sqlite3
AI_VASTU_RAZORPAY_KEY_ID=
AI_VASTU_RAZORPAY_KEY_SECRET=
AI_VASTU_RAZORPAY_WEBHOOK_SECRET=
AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID=
AI_VASTU_RAZORPAY_YEARLY_PLAN_ID=
AI_VASTU_SUPABASE_JWT_AUDIENCE=authenticated
""".lstrip()
    if "AI_VASTU_RAZORPAY_KEY_ID=" not in text:
        text = text.rstrip() + "\n\n" + block
    path.write_text(text, encoding="utf-8")


patch_package_json()
patch_api_main()
patch_env_example()

print("Phase 23 pricing, billing, entitlement, and checkout scripts integrated.")
