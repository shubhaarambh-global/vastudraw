from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, cast

RuntimeEnvironment = Literal["development", "test", "staging", "production"]
_ALLOWED_RUNTIME_ENVIRONMENTS = frozenset(
    {"development", "test", "staging", "production"}
)


class RuntimeEnvironmentConfigurationError(RuntimeError):
    pass


def parse_runtime_environment(
    environment: Mapping[str, str],
) -> RuntimeEnvironment:
    raw = environment.get("APP_ENV")
    if raw is None:
        return "development"
    normalized = raw.strip().lower()
    if normalized not in _ALLOWED_RUNTIME_ENVIRONMENTS:
        raise RuntimeEnvironmentConfigurationError(
            "APP_ENV must be development, test, staging, or production."
        )
    return cast(RuntimeEnvironment, normalized)
