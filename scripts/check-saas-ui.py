from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "apps/web/src/components/shell/SaasShell.tsx"
NAVIGATION = ROOT / "apps/web/src/components/shell/navigation.ts"
DASHBOARD = ROOT / "apps/web/src/components/dashboard/DashboardPage.tsx"
PROJECTS = ROOT / "apps/web/src/components/projects/ProjectsPage.tsx"
CSS = ROOT / "apps/web/src/app/globals.css"

for required in (SHELL, NAVIGATION, DASHBOARD, PROJECTS, CSS):
    if not required.exists():
        raise SystemExit(f"Missing Phase 21 SaaS UI file: {required.relative_to(ROOT)}")

shell_source = SHELL.read_text(encoding="utf-8")
navigation_source = NAVIGATION.read_text(encoding="utf-8")
dashboard_source = DASHBOARD.read_text(encoding="utf-8")
projects_source = PROJECTS.read_text(encoding="utf-8")
css_source = CSS.read_text(encoding="utf-8")

for label in ("Dashboard", "Projects", "Editor", "Generation", "Reviews", "Exports", "Settings"):
    if label not in navigation_source:
        raise SystemExit(f"Sidebar navigation missing: {label}")

if 'aria-current={active ? "page" : undefined}' not in shell_source:
    raise SystemExit("Active sidebar page is not exposed with aria-current.")

if "Production Vastu v1" not in shell_source:
    raise SystemExit("Frozen Vastu production status is missing from the SaaS shell.")

if "82%" in dashboard_source or "Vastu Score" in dashboard_source:
    raise SystemExit("Phase 21 must not display fabricated project Vastu scores.")

if "workspace.projects" not in dashboard_source or "workspace.projects" not in projects_source:
    raise SystemExit("Dashboard/projects UI is not bound to live project records.")

if ".saas-sidebar" not in css_source or '.saas-nav-item[data-active="true"]' not in css_source:
    raise SystemExit("Phase 21 sidebar/active-state styling is incomplete.")

print(
    "Phase 21 SaaS UI wired: "
    "sidebar=true, active_page=true, dashboard=true, projects=true, "
    "editor_shell=true, vastu_status=source_backed, fabricated_score=false"
)
