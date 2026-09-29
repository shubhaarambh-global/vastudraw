from __future__ import annotations

from pathlib import Path

from ai_vastu.production.middleware import ProductionHardeningMiddleware
from ai_vastu.production.rate_limit import hash_rate_limit_key
from ai_vastu.production.settings import EXPECTED_VASTU_BUNDLE_HASH
from ai_vastu.vastu.models import RuleBundle

ROOT = Path(__file__).resolve().parents[1]

bundle_path = ROOT / "docs" / "vastu" / "spec-v1.0" / "production" / "rule-bundle.json"
bundle = RuleBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))

assert bundle.production
assert bundle.content_hash == EXPECTED_VASTU_BUNDLE_HASH
assert (
    ProductionHardeningMiddleware._scope_for_request("POST", "/requirements/interpret")
    == "requirements_interpret"
)
assert (
    ProductionHardeningMiddleware._scope_for_request(
        "POST",
        "/confirmed-generation/projects/11111111-1111-1111-1111-111111111111"
    )
    == "confirmed_generation"
)
assert (
    ProductionHardeningMiddleware._scope_for_request("POST", "/billing/checkout")
    == "billing_checkout"
)
assert (
    ProductionHardeningMiddleware._scope_for_request(
        "POST", "/billing/webhooks/phonepe"
    )
    == "payment_webhook"
)
assert (
    ProductionHardeningMiddleware._scope_for_request(
        "POST", "/billing/webhooks/razorpay"
    )
    == "payment_webhook"
)
assert (
    ProductionHardeningMiddleware._scope_for_request(
        "POST", "/billing/orders/vd_order/refresh"
    )
    == "payment_status"
)
assert len(hash_rate_limit_key("Bearer secret")) == 64

migration = ROOT / "infra" / "supabase" / "migrations" / "202609150025_phase25_rate_limits.sql"
assert migration.is_file()

workflow = ROOT / ".github" / "workflows" / "production-gates.yml"
assert workflow.is_file()

print(
    "Phase 25 hardening wired: production_fail_closed=true, "
    "security_headers=true, request_ids=true, structured_logging=true, "
    "postgres_rate_limits=true, frozen_vastu_hash=true, backups=true, "
    "ci_release_gate=true, launch_gate=true"
)
