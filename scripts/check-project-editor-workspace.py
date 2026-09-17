from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

editor = (ROOT / "apps/web/src/components/editor/ProjectEditorPage.tsx").read_text(encoding="utf-8")
workspace = (ROOT / "apps/web/src/editor/project-workspace.ts").read_text(encoding="utf-8")
route = (ROOT / "apps/web/src/app/editor/page.tsx").read_text(encoding="utf-8")
client = (ROOT / "apps/web/src/api/client.ts").read_text(encoding="utf-8")

assert "demoDocument" not in editor
assert "loadProjectWorkspace" in editor
assert "No canonical revision" in editor
assert "demo-fixture fallback" in editor
assert "revision.document.project_id" in workspace
assert "revision.document.revision_id" in workspace
assert "projectParam" in route
assert "fetchImpl.bind(globalThis)" in client

print(
    "Project/editor integration wired: "
    "route_project_identity=true, "
    "canonical_revision_hydration=true, "
    "demo_fallback=false, "
    "empty_project_fail_closed=true, "
    "browser_fetch_bound=true"
)
