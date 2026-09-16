from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase23_routes_and_pricing_pages_exist() -> None:
    assert (ROOT / "apps/api/app/billing_routes.py").exists()
    assert (ROOT / "apps/web/src/app/pricing/page.tsx").exists()
    assert (ROOT / "apps/web/src/app/billing/page.tsx").exists()


def test_phase23_keeps_frozen_vastu_files_out_of_scope() -> None:
    apply_source = (ROOT / "scripts/apply-phase23.py").read_text(encoding="utf-8")
    assert "docs/vastu/spec-v1.0/production" not in apply_source
    assert "rule-bundle.json" not in apply_source


def test_phase23_has_server_authoritative_billing_gate() -> None:
    service = (
        ROOT / "python/ai_vastu/billing/service.py"
    ).read_text(encoding="utf-8")
    assert "authorize_generation" in service
    assert "record_successful_generation" in service
    assert "free_trial_pending" in service
    assert "project_credit" in service
