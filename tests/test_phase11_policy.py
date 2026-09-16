from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_projects_domain_has_no_geometry_solver_or_cad_vendor_imports() -> None:
    for path in (ROOT / "python/ai_vastu/projects").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "from shapely" not in text
        assert "import pyclipr" not in text
        assert "from ortools" not in text
        assert "import ezdxf" not in text


def test_revision_storage_is_append_only_at_api_boundary() -> None:
    text = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
    assert '@app.post(\n        "/projects/{project_id}/revisions"' in text
    assert '@app.put("/projects/{project_id}/revisions' not in text
    assert '@app.patch("/projects/{project_id}/revisions' not in text


def test_project_smoke_fixture_is_not_imported_from_tests() -> None:
    text = (ROOT / "scripts/check-project-revisions.py").read_text(encoding="utf-8")
    assert "from tests" not in text
