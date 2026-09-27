from __future__ import annotations

import os
from collections.abc import Mapping

from ai_vastu.runtime_environment import (
    RuntimeEnvironmentConfigurationError,
    parse_runtime_environment,
)

from .errors import ProjectStoreConfigurationError
from .postgres_repository import PostgresProjectRepository
from .repository import ProjectRepository
from .sqlite_repository import SqliteProjectRepository

_PRODUCTION_ENVIRONMENTS = frozenset({"production", "staging"})


def _parse_int(
    environment: Mapping[str, str],
    name: str,
    default: int,
    *,
    minimum: int,
) -> int:
    raw = environment.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ProjectStoreConfigurationError(f"{name} must be an integer.") from exc
    if value < minimum:
        raise ProjectStoreConfigurationError(f"{name} must be >= {minimum}.")
    return value


def create_project_repository_from_environment(
    environment: Mapping[str, str] | None = None,
) -> ProjectRepository:
    env = os.environ if environment is None else environment
    try:
        app_env = parse_runtime_environment(env)
    except RuntimeEnvironmentConfigurationError as exc:
        raise ProjectStoreConfigurationError(str(exc)) from exc
    database_url = env.get("AI_VASTU_DATABASE_URL", "").strip()

    if database_url:
        min_size = _parse_int(env, "AI_VASTU_DB_POOL_MIN_SIZE", 1, minimum=1)
        max_size = _parse_int(env, "AI_VASTU_DB_POOL_MAX_SIZE", 10, minimum=min_size)
        timeout = _parse_int(env, "AI_VASTU_DB_POOL_TIMEOUT_SECONDS", 10, minimum=1)
        return PostgresProjectRepository(
            database_url,
            min_pool_size=min_size,
            max_pool_size=max_size,
            pool_timeout_seconds=float(timeout),
        )

    if app_env in _PRODUCTION_ENVIRONMENTS:
        raise ProjectStoreConfigurationError(
            "AI_VASTU_DATABASE_URL is required when APP_ENV is production or staging."
        )

    return SqliteProjectRepository(env.get("AI_VASTU_SQLITE_PATH", ":memory:"))
