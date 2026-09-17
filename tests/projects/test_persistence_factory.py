from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import pytest

from ai_vastu.projects import ProjectStoreConfigurationError, SqliteProjectRepository
from ai_vastu.projects import factory as persistence_factory


class StubPostgresRepository:
    def __init__(
        self,
        database_url: str,
        *,
        min_pool_size: int,
        max_pool_size: int,
        pool_timeout_seconds: float,
    ) -> None:
        self.database_url = database_url
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool_timeout_seconds = pool_timeout_seconds

    def close(self) -> None:
        return None


def test_development_defaults_to_sqlite_reference_adapter() -> None:
    repository = persistence_factory.create_project_repository_from_environment(
        {"APP_ENV": "development"}
    )
    assert isinstance(repository, SqliteProjectRepository)
    repository.close()


def test_production_fails_closed_without_postgres_url() -> None:
    with pytest.raises(ProjectStoreConfigurationError):
        persistence_factory.create_project_repository_from_environment({"APP_ENV": "production"})


def test_database_url_selects_postgres_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        persistence_factory,
        "PostgresProjectRepository",
        StubPostgresRepository,
    )
    environment: Mapping[str, str] = {
        "APP_ENV": "production",
        "AI_VASTU_DATABASE_URL": "postgresql://example.invalid/postgres",
        "AI_VASTU_DB_POOL_MIN_SIZE": "2",
        "AI_VASTU_DB_POOL_MAX_SIZE": "8",
        "AI_VASTU_DB_POOL_TIMEOUT_SECONDS": "15",
    }
    repository = persistence_factory.create_project_repository_from_environment(environment)
    stub = cast(StubPostgresRepository, repository)
    assert stub.database_url == "postgresql://example.invalid/postgres"
    assert stub.min_pool_size == 2
    assert stub.max_pool_size == 8
    assert stub.pool_timeout_seconds == 15.0
