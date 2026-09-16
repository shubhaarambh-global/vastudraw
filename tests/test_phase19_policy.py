from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase19_removes_only_authorization_release_blocker() -> None:
    source = (ROOT / "python/ai_vastu/release/readiness.py").read_text(encoding="utf-8")
    assert "AUTHORIZATION_IMPLEMENTED" in source
    assert "AUTHORIZATION_NOT_IMPLEMENTED" not in source
    assert "VASTU_SPEC_NOT_FROZEN" in source
    assert "VASTU_RULESET_EMPTY" in source
    assert "VASTU_RULE_BUNDLE_NOT_PINNED" in source


def test_supabase_auth_uses_asymmetric_jwks_and_production_fails_closed() -> None:
    source = (ROOT / "python/ai_vastu/auth/verifier.py").read_text(encoding="utf-8")
    assert ".well-known/jwks.json" in source
    assert '"ES256"' in source
    assert '"RS256"' in source
    assert '"HS256"' not in source
    assert "Development authentication is forbidden" in source


def test_project_ownership_is_persisted_separately_from_plan_document() -> None:
    migration = (
        ROOT / "infra/postgres/migrations/202609150002_phase19_project_ownership.sql"
    ).read_text(encoding="utf-8")
    assert "ai_vastu_project_owners" in migration
    assert "owner_user_id UUID NOT NULL" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration

    plan_source = (ROOT / "python/ai_vastu/plan_schema/models.py").read_text(
        encoding="utf-8"
    )
    assert "owner_user_id" not in plan_source


def test_dashboard_is_real_root_route_and_editor_remains_available() -> None:
    root_page = (ROOT / "apps/web/src/app/page.tsx").read_text(encoding="utf-8")
    editor_page = (ROOT / "apps/web/src/app/editor/page.tsx").read_text(encoding="utf-8")
    assert "DashboardPage" in root_page
    assert "ProjectEditorPage" in editor_page
    assert "DemoEditorPage" not in editor_page


def test_editor_grid_does_not_feed_fractional_viewport_bounds_to_canonical_transform() -> None:
    source = (
        ROOT / "apps/web/src/components/editor/PlanEditor.tsx"
    ).read_text(encoding="utf-8")

    assert "y_mm: bounds.minYmm" not in source
    assert "y_mm: bounds.maxYmm" not in source
    assert "x_mm: bounds.minXmm" not in source
    assert "x_mm: bounds.maxXmm" not in source

    assert (
        "points={[screen.xPx, 0, screen.xPx, props.size.heightPx]}"
        in source
    )
    assert (
        "points={[0, screen.yPx, props.size.widthPx, screen.yPx]}"
        in source
    )
