from __future__ import annotations

from pathlib import Path

import pytest
from tests.production.test_settings import base_environment

from ai_vastu.nvidia_nim_http import (
    NVIDIA_NIM_API_BASE,
    PRIMARY_REASONING_MODEL,
    VISION_PLAN_MODEL,
)
from ai_vastu.production.settings import (
    ProductionConfigurationError,
    load_production_settings,
)


def _environment(tmp_path: Path) -> dict[str, str]:
    return base_environment(tmp_path)


def test_production_settings_accept_pinned_nvidia_nim_stack(tmp_path: Path) -> None:
    settings = load_production_settings(_environment(tmp_path))

    assert settings.requirements_provider == "nvidia_nim"
    assert settings.nvidia_base_url == NVIDIA_NIM_API_BASE
    assert settings.nvidia_primary_model == PRIMARY_REASONING_MODEL
    assert settings.nvidia_vision_model == VISION_PLAN_MODEL
    assert settings.plan_recognition_provider == "nvidia_nim"
    assert settings.plan_recognition_model == VISION_PLAN_MODEL


@pytest.mark.parametrize(
    "name",
    [
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "AI_VASTU_ARCHITECT_PROVIDER",
        "AI_VASTU_VASTU_PROVIDER",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
        "AI_VASTU_REVISION_PROVIDER",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER",
    ],
)
@pytest.mark.parametrize(
    "value",
    ["", "fixture", "openrouter", "gemini", "ollama_local"],
)
def test_production_settings_reject_provider_drift(
    tmp_path: Path, name: str, value: str
) -> None:
    environment = _environment(tmp_path)
    environment[name] = value

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(environment)


@pytest.mark.parametrize(
    "name",
    [
        "AI_VASTU_NVIDIA_PRIMARY_MODEL",
        "AI_VASTU_NVIDIA_VISION_MODEL",
    ],
)
def test_production_settings_require_explicit_pinned_nvidia_models(
    tmp_path: Path, name: str
) -> None:
    environment = _environment(tmp_path)
    environment.pop(name)

    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(environment)


def test_production_settings_require_nvidia_server_secret(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    environment["NVIDIA_API_KEY"] = " "

    with pytest.raises(ProductionConfigurationError, match="NVIDIA_API_KEY"):
        load_production_settings(environment)


def test_legacy_credentials_are_not_required_or_exposed(tmp_path: Path) -> None:
    environment = _environment(tmp_path)
    environment.pop("OPENROUTER_API_KEY", None)
    environment.pop("GEMINI_API_KEY", None)

    summary = str(load_production_settings(environment).redacted_summary()).lower()

    assert "openrouter" not in summary
    assert "gemini" not in summary
