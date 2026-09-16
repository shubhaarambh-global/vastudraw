from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_postgres_vendor_imports_are_confined_to_persistence_adapter() -> None:
    projects_root = ROOT / "python/ai_vastu/projects"
    for path in projects_root.glob("*.py"):
        if path.name in {"postgres_repository.py", "factory.py", "__init__.py"}:
            continue
        source = path.read_text(encoding="utf-8")
        assert "import psycopg" not in source
        assert "from psycopg" not in source
        assert "from psycopg_pool" not in source


def test_phase18_migration_keeps_revisions_append_only() -> None:
    migration = (
        ROOT / "infra/postgres/migrations/202609150001_phase18_project_store.sql"
    ).read_text(encoding="utf-8")
    assert "PRIMARY KEY (project_id, revision_id)" in migration
    assert "UNIQUE (project_id, revision_number)" in migration
    assert "ON DELETE RESTRICT" in migration
    assert "ON DELETE CASCADE" not in migration
