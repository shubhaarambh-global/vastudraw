from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_pyproject() -> None:
    path = ROOT / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    dependency = '  "psycopg[binary,pool]>=3.2,<4",\n'
    if "psycopg[binary,pool]" not in text:
        marker = '  "Pillow==12.3.0",\n'
        if marker not in text:
            raise SystemExit("Could not locate Python dependency insertion point.")
        text = text.replace(marker, marker + dependency, 1)
    path.write_text(text, encoding="utf-8")


def patch_errors() -> None:
    path = ROOT / "python/ai_vastu/projects/errors.py"
    text = path.read_text(encoding="utf-8")
    block = (
        "\n\nclass ProjectStoreConfigurationError(ProjectStoreError):\n"
        "    \"\"\"Raised when production persistence configuration is unsafe.\"\"\"\n"
    )
    if "class ProjectStoreConfigurationError" not in text:
        text = text.rstrip() + block + "\n"
    path.write_text(text, encoding="utf-8")


def patch_repository_protocol() -> None:
    path = ROOT / "python/ai_vastu/projects/repository.py"
    text = path.read_text(encoding="utf-8")
    if "    def close(self) -> None: ..." not in text:
        marker = "class ProjectRepository(Protocol):\n"
        text = text.replace(marker, marker + "    def close(self) -> None: ...\n\n", 1)
    path.write_text(text, encoding="utf-8")


def patch_projects_init() -> None:
    path = ROOT / "python/ai_vastu/projects/__init__.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "    ProjectNotFoundError,\n",
        "    ProjectNotFoundError,\n    ProjectStoreConfigurationError,\n",
        1,
    ) if "ProjectStoreConfigurationError" not in text else text
    if "from .factory import create_project_repository_from_environment" not in text:
        text = text.replace(
            "from .models import (\n",
            "from .factory import create_project_repository_from_environment\n"
            "from .models import (\n",
            1,
        )
    if "from .postgres_repository import PostgresProjectRepository" not in text:
        text = text.replace(
            "from .repository import ProjectRepository\n",
            "from .postgres_repository import PostgresProjectRepository\n"
            "from .repository import ProjectRepository\n",
            1,
        )
    additions = (
        '    "PostgresProjectRepository",\n'
        '    "ProjectStoreConfigurationError",\n'
        '    "create_project_repository_from_environment",\n'
    )
    if '    "PostgresProjectRepository",' not in text:
        marker = '    "PersistenceCorruptionError",\n'
        text = text.replace(marker, marker + additions, 1)
    path.write_text(text, encoding="utf-8")


def patch_api() -> None:
    path = ROOT / "apps/api/app/main.py"
    text = path.read_text(encoding="utf-8")
    if "from collections.abc import AsyncIterator" not in text:
        text = text.replace(
            "import json\nimport os\n",
            "import json\nimport os\nfrom collections.abc import AsyncIterator\n"
            "from contextlib import asynccontextmanager\n",
            1,
        )
    text = text.replace('version="0.17.0"', 'version="0.18.0"')
    text = text.replace('"phase": "17"', '"phase": "18"')
    if "create_project_repository_from_environment" not in text:
        text = text.replace(
            "    SqliteProjectRepository,\n",
            "    SqliteProjectRepository,\n    create_project_repository_from_environment,\n",
            1,
        )
    old = (
        "def create_app(repository: ProjectRepository | None = None) -> FastAPI:\n"
        '    app = FastAPI(title="AI Vastu Architect API", version="0.18.0")\n'
        "    project_repository = repository or SqliteProjectRepository(\n"
        '        os.environ.get("AI_VASTU_SQLITE_PATH", ":memory:")\n'
        "    )\n"
        "    app.state.project_service = ProjectRevisionService(project_repository)\n"
    )
    new = (
        "def create_app(repository: ProjectRepository | None = None) -> FastAPI:\n"
        "    project_repository = (\n"
        "        repository\n"
        "        if repository is not None\n"
        "        else create_project_repository_from_environment()\n"
        "    )\n\n"
        "    @asynccontextmanager\n"
        "    async def lifespan(_: FastAPI) -> AsyncIterator[None]:\n"
        "        try:\n"
        "            yield\n"
        "        finally:\n"
        "            project_repository.close()\n\n"
        "    app = FastAPI(\n"
        '        title="AI Vastu Architect API",\n'
        '        version="0.18.0",\n'
        "        lifespan=lifespan,\n"
        "    )\n"
        "    app.state.project_service = ProjectRevisionService(project_repository)\n"
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif "create_project_repository_from_environment()" not in text:
        raise SystemExit("Could not locate Phase 17 API repository bootstrap.")
    # Sqlite import is no longer needed after factory wiring.
    text = text.replace("    SqliteProjectRepository,\n", "")
    path.write_text(text, encoding="utf-8")


def patch_health_test() -> None:
    path = ROOT / "apps/api/tests/test_health.py"
    text = path.read_text(encoding="utf-8")
    for phase in ("11", "15", "16", "17"):
        text = text.replace(f'"phase": "{phase}"', '"phase": "18"')
    path.write_text(text, encoding="utf-8")


def patch_readiness() -> None:
    path = ROOT / "python/ai_vastu/release/readiness.py"
    text = path.read_text(encoding="utf-8")
    old = (
        '            _gate(\n'
        '                "PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED",\n'
        '                ReleaseGateStatus.BLOCKER,\n'
        '                (\n'
        '                    "The current SQLite repository is a reference adapter, "\n'
        '                    "not the planned production store."\n'
        '                ),\n'
        '            ),\n'
    )
    new = (
        '            _gate(\n'
        '                "PRODUCTION_PERSISTENCE_IMPLEMENTED",\n'
        '                ReleaseGateStatus.PASS,\n'
        '                (\n'
        '                    "PostgreSQL/Supabase production persistence is implemented behind "\n'
        '                    "the ProjectRepository boundary."\n'
        '                ),\n'
        '                "backend=postgresql",\n'
        '                "driver=psycopg3",\n'
        '                "sqlite_reference_only=true",\n'
        '                "production_without_database_url=fail_closed",\n'
        '            ),\n'
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif "PRODUCTION_PERSISTENCE_IMPLEMENTED" not in text:
        raise SystemExit("Could not locate Phase 17 production persistence blocker.")
    path.write_text(text, encoding="utf-8")


def patch_release_expectations() -> None:
    for relative in ("scripts/check-production-mvp.py", "tests/release/test_readiness.py"):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        text = text.replace('    "PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED",\n', "")
        text = text.replace('        "PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED",\n', "")
        text = text.replace("Phase 17 expected", "Phase 18 expected")
        path.write_text(text, encoding="utf-8")

    for relative in (
        "tests/test_phase15_policy.py",
        "tests/test_phase16_policy.py",
        "tests/test_phase17_policy.py",
    ):
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            'assert "PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED" in source',
            'assert "PRODUCTION_PERSISTENCE_IMPLEMENTED" in source',
        )
        path.write_text(text, encoding="utf-8")


def patch_package() -> None:
    path = ROOT / "package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = payload["scripts"]
    scripts["persistence:check"] = "python scripts/check-production-persistence.py"
    scripts["persistence:live"] = "python scripts/check-postgres-live.py"
    validate = scripts["validate"]
    if "pnpm persistence:check" not in validate:
        needle = "pnpm web-api:check && pnpm mvp:check"
        replacement = "pnpm web-api:check && pnpm persistence:check && pnpm mvp:check"
        if needle not in validate:
            raise SystemExit("Could not locate Phase 17 validation insertion point.")
        scripts["validate"] = validate.replace(needle, replacement, 1)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def patch_env() -> None:
    path = ROOT / ".env.example"
    text = path.read_text(encoding="utf-8")
    additions = """

# Phase 18 production persistence
# Required when APP_ENV=production or APP_ENV=staging.
# Copy the exact PostgreSQL URL from your Supabase/Postgres provider; never commit credentials.
AI_VASTU_DATABASE_URL=
AI_VASTU_DB_POOL_MIN_SIZE=1
AI_VASTU_DB_POOL_MAX_SIZE=10
AI_VASTU_DB_POOL_TIMEOUT_SECONDS=10
# Local/reference adapter only:
AI_VASTU_SQLITE_PATH=:memory:
"""
    if "AI_VASTU_DATABASE_URL" not in text:
        text = text.rstrip() + additions
    path.write_text(text, encoding="utf-8")


def patch_docs() -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    heading = "# Phase 18 — PostgreSQL/Supabase production persistence"
    if heading not in text:
        text = text.rstrip() + "\n\n" + (ROOT / "PHASE18.md").read_text(encoding="utf-8") + "\n"
    path.write_text(text, encoding="utf-8")


def patch_phase18_policy() -> None:
    path = ROOT / "tests/test_phase18_policy.py"
    if path.exists():
        return
    content = (
        "from pathlib import Path\n\n"
        "ROOT = Path(__file__).resolve().parents[1]\n\n\n"
        "def test_phase18_removes_only_persistence_release_blocker() -> None:\n"
        "    source = (\n"
        "        ROOT / \"python/ai_vastu/release/readiness.py\"\n"
        "    ).read_text(encoding=\"utf-8\")\n"
        "    assert \"PRODUCTION_PERSISTENCE_IMPLEMENTED\" in source\n"
        "    assert \"PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED\" not in source\n"
        "    assert \"AUTHORIZATION_NOT_IMPLEMENTED\" in source\n"
        "    assert \"VASTU_SPEC_NOT_FROZEN\" in source\n\n\n"
        "def test_production_repository_uses_postgres_transaction_boundary() -> None:\n"
        "    source = (\n"
        "        ROOT / \"python/ai_vastu/projects/postgres_repository.py\"\n"
        "    ).read_text(encoding=\"utf-8\")\n"
        "    assert \"FOR UPDATE\" in source\n"
        "    assert \"connection.transaction()\" in source\n"
        "    assert \"prepare_threshold\" in source\n"
    )
    path.write_text(content, encoding="utf-8")


def main() -> None:
    patch_pyproject()
    patch_errors()
    patch_repository_protocol()
    patch_projects_init()
    patch_api()
    patch_health_test()
    patch_readiness()
    patch_release_expectations()
    patch_package()
    patch_env()
    patch_docs()
    patch_phase18_policy()
    print("Phase 18 integration applied.")


if __name__ == "__main__":
    main()
