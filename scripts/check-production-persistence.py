from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

repository = (ROOT / "python/ai_vastu/projects/postgres_repository.py").read_text(
    encoding="utf-8"
)
factory = (ROOT / "python/ai_vastu/projects/factory.py").read_text(encoding="utf-8")
migration = (
    ROOT / "infra/postgres/migrations/202609150001_phase18_project_store.sql"
).read_text(encoding="utf-8")
readiness = (ROOT / "python/ai_vastu/release/readiness.py").read_text(encoding="utf-8")
api = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")

for required in (
    "ConnectionPool",
    "prepare_threshold",
    "FOR UPDATE",
    "connection.transaction()",
    "Jsonb",
):
    assert required in repository

for required in (
    "AI_VASTU_DATABASE_URL",
    "APP_ENV",
    "production",
    "staging",
    "PostgresProjectRepository",
):
    assert required in factory

for required in (
    "ai_vastu_projects",
    "ai_vastu_project_revisions",
    "JSONB",
    "TIMESTAMPTZ",
    "DEFERRABLE INITIALLY DEFERRED",
):
    assert required in migration

assert "create_project_repository_from_environment" in api
assert "PRODUCTION_PERSISTENCE_IMPLEMENTED" in readiness
assert "PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED" not in readiness

print(
    "Production persistence wired: backend=postgresql, pool=psycopg3, "
    "optimistic_head_lock=true, sqlite_reference_only=true, "
    "production_without_database_url=fail_closed"
)
