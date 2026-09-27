from __future__ import annotations

import pytest

from ai_vastu.auth import (
    AuthConfigurationError,
    create_access_token_verifier_from_environment,
)
from ai_vastu.projects import (
    ProjectStoreConfigurationError,
    create_project_repository_from_environment,
)
from ai_vastu.runtime_environment import (
    RuntimeEnvironmentConfigurationError,
    parse_runtime_environment,
)
from app import main


def test_runtime_environment_normalizes_only_explicit_supported_values() -> None:
    assert parse_runtime_environment({}) == "development"
    assert parse_runtime_environment({"APP_ENV": " Production "}) == "production"
    assert parse_runtime_environment({"APP_ENV": "TEST"}) == "test"


@pytest.mark.parametrize("value", ("prod", "qa", "", "local"))
def test_unknown_runtime_environment_fails_closed_in_security_factories(
    value: str,
) -> None:
    with pytest.raises(AuthConfigurationError, match="APP_ENV must be"):
        create_access_token_verifier_from_environment({"APP_ENV": value})
    with pytest.raises(ProjectStoreConfigurationError, match="APP_ENV must be"):
        create_project_repository_from_environment({"APP_ENV": value})


def test_unknown_runtime_environment_stops_api_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "prod")

    with pytest.raises(RuntimeEnvironmentConfigurationError, match="APP_ENV must be"):
        main.create_app()
