from __future__ import annotations

import hashlib
from pathlib import Path

from ai_vastu.billing.catalog import get_product
from ai_vastu.billing.phonepe import validate_callback_authorization

ROOT = Path(__file__).resolve().parents[1]

expected_prices = {
    "free_first_generation": 0,
    "project_single": 39_900,
    "project_pack_10": 339_900,
    "pro_monthly": 249_900,
    "pro_yearly": 2_499_900,
}
for sku, amount in expected_prices.items():
    assert get_product(sku).amount_paise == amount

official_vector = hashlib.sha256(b"username:password").hexdigest()
assert official_vector == "bc842c31a9e54efe320d30d948be61291f3ceee4766e36ab25fa65243cd76e0e"
assert validate_callback_authorization("username", "password", official_vector)

migration = ROOT / "infra/postgres/migrations/202609270001_phase29d_payment_atomicity.sql"
source = migration.read_text(encoding="utf-8")
for needle in (
    "billing_payment_orders",
    "ENABLE ROW LEVEL SECURITY",
    "REVOKE ALL ON TABLE public.billing_accounts FROM PUBLIC",
    "REVOKE ALL ON TABLE public.billing_payment_orders FROM authenticated",
):
    assert needle in source

routes = (ROOT / "apps/api/app/billing_routes.py").read_text(encoding="utf-8")
for needle in (
    'router.post("/checkout")',
    'router.post("/webhooks/phonepe")',
    'router.post("/orders/{merchant_order_id}/refresh")',
    "apply_payment_order_event",
):
    assert needle in routes

print(
    "Phase 29D offline gate: prices=true, phonepe_v2=true, "
    "atomic_fulfillment=true, reconciliation=true, billing_rls=true"
)
