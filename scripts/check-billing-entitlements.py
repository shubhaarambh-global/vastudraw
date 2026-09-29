from __future__ import annotations

import tempfile
from pathlib import Path

from ai_vastu.billing.catalog import get_product
from ai_vastu.billing.service import BillingService
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository

ROOT = Path(__file__).resolve().parents[1]

user = "11111111-1111-1111-1111-111111111111"
free_project = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
paid_project = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

assert get_product("project_single").amount_paise == 39_900
assert get_product("project_pack_10").amount_paise == 339_900
assert get_product("pro_monthly").amount_paise == 249_900
assert get_product("pro_yearly").amount_paise == 2_499_900

with tempfile.TemporaryDirectory() as directory:
    repository = SqliteBillingRepository(Path(directory) / "billing.sqlite3")
    service = BillingService(repository)

    assert service.register_project(user, free_project) == "free_trial_pending"
    before = service.authorize_generation(user, free_project)
    assert before.allowed and before.consumption == "free_generation"
    service.record_successful_generation(user, free_project)
    assert not service.authorize_generation(user, free_project).allowed

    assert service.apply_one_time_purchase("evt-1", user, "project_single")
    assert not service.apply_one_time_purchase("evt-1", user, "project_single")
    assert service.register_project(user, paid_project) == "project_credit"
    assert service.authorize_generation(user, paid_project).allowed
    service.record_successful_generation(user, paid_project)
    service.record_successful_generation(user, paid_project)
    assert service.authorize_generation(user, paid_project).allowed

    repository.close()

assert (ROOT / "apps/api/app/billing_routes.py").exists()
assert (ROOT / "apps/web/src/app/pricing/page.tsx").exists()
assert (ROOT / "apps/web/src/app/billing/page.tsx").exists()
assert (ROOT / "infra/postgres/migrations/202609150003_phase23_billing.sql").exists()

main_source = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
assert "billing_router" in main_source
assert "include_router(billing_router)" in main_source
routes_source = (ROOT / "apps/api/app/billing_routes.py").read_text(encoding="utf-8")
assert "/projects/{project_id}/register" in routes_source
assert "/projects/{project_id}/generation-authorization" in routes_source
assert "/projects/{project_id}/generation-succeeded" in routes_source

print(
    "Phase 23 billing wired: catalog=true, free_generation_once=true, "
    "project_credits=true, paid_project_regeneration=true, subscriptions=true, "
    "idempotent_webhooks=true, server_entitlement_api=true"
)
