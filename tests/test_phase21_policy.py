from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase21_saas_navigation_has_real_routes_and_active_state() -> None:
    navigation = (
        ROOT / "apps/web/src/components/shell/navigation.ts"
    ).read_text(encoding="utf-8")
    shell = (
        ROOT / "apps/web/src/components/shell/SaasShell.tsx"
    ).read_text(encoding="utf-8")

    for route in (
        'href: "/"',
        'href: "/projects"',
        'href: "/editor"',
        'href: "/generation"',
        'href: "/reviews"',
        'href: "/exports"',
        'href: "/settings"',
    ):
        assert route in navigation

    assert 'aria-current={active ? "page" : undefined}' in shell


def test_phase21_dashboard_does_not_fabricate_project_compliance_score() -> None:
    dashboard = (
        ROOT / "apps/web/src/components/dashboard/DashboardPage.tsx"
    ).read_text(encoding="utf-8")

    assert "82%" not in dashboard
    assert "Vastu Score" not in dashboard
    assert "workspace.projects" in dashboard
    assert "Production rules" in dashboard


def test_phase21_keeps_existing_editor_project_bound() -> None:
    editor_route = (ROOT / "apps/web/src/app/editor/page.tsx").read_text(encoding="utf-8")
    project_editor = (
        ROOT / "apps/web/src/components/editor/ProjectEditorPage.tsx"
    ).read_text(encoding="utf-8")

    assert "SaasShell" in editor_route
    assert "ProjectEditorPage" in editor_route
    assert "projectId={projectId}" in editor_route
    assert "loadProjectWorkspace(api, projectId)" in project_editor
    assert "DemoEditorPage" not in editor_route
