from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

client = (ROOT / "apps/web/src/api/client.ts").read_text(encoding="utf-8")
panel = (ROOT / "apps/web/src/components/editor/ProjectWorkflowPanel.tsx").read_text(
    encoding="utf-8"
)
page = (ROOT / "apps/web/src/components/editor/DemoEditorPage.tsx").read_text(encoding="utf-8")
readiness = (ROOT / "python/ai_vastu/release/readiness.py").read_text(encoding="utf-8")
api = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")

for endpoint in (
    '"/projects"',
    '"/generation/architectural"',
):
    assert endpoint in client
assert "loadCurrentRevision" in client
assert "appendRevision" in client
assert "ProjectWorkflowPanel" in page
assert "Save canonical revision" in panel
assert "Run deterministic generation" in panel
assert "WEB_API_WORKFLOW_IMPLEMENTED" in readiness
assert "WEB_API_WORKFLOW_NOT_IMPLEMENTED" not in readiness
assert "CORSMiddleware" in api

print(
    "Web/API workflow wired: create=true, load=true, save=true, generation=true, "
    "cors=true, release_blocker_removed=true"
)
