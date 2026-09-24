from __future__ import annotations

from pathlib import Path

import pytest
from tests.production.test_settings import base_environment

from ai_vastu.openrouter_http import FALLBACK_REASONING_MODEL, PRIMARY_ARCHITECTURAL_MODEL
from ai_vastu.production.settings import (
    ProductionConfigurationError,
    load_production_settings,
)


def _environment(tmp_path: Path) -> dict[str, str]:
    return base_environment(tmp_path)


def test_production_settings_accept_pinned_hybrid_stack(
    tmp_path: Path,
) -> None:
    settings = load_production_settings(_environment(tmp_path))

    assert settings.requirements_provider == "openrouter"
    assert settings.openrouter_primary_model == PRIMARY_ARCHITECTURAL_MODEL
    assert settings.openrouter_fallback_model == FALLBACK_REASONING_MODEL
    assert settings.plan_recognition_provider == "gemini"
    assert settings.plan_recognition_model == "gemini-3.1-flash-lite"
    assert settings.openai_model is None
    assert settings.gemini_model == "gemini-3.1-flash-lite"


def test_production_settings_reject_paid_model_substitution(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    env["AI_VASTU_OPENROUTER_PRIMARY_MODEL"] = "deepseek/deepseek-v4-flash-0731"

    with pytest.raises(ProductionConfigurationError):
        load_production_settings(env)


@pytest.mark.parametrize(
    "name",
    [
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "AI_VASTU_ARCHITECT_PROVIDER",
        "AI_VASTU_VASTU_PROVIDER",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
        "AI_VASTU_REVISION_PROVIDER",
    ],
)
@pytest.mark.parametrize("value", ["", "fixture", "gemini"])
def test_production_settings_reject_text_provider_drift(
    tmp_path: Path, name: str, value: str
) -> None:
    env = _environment(tmp_path)
    env[name] = value
    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)


@pytest.mark.parametrize(
    "name", [
        "AI_VASTU_OPENROUTER_PRIMARY_MODEL",
        "AI_VASTU_OPENROUTER_VISION_MODEL",
        "AI_VASTU_OPENROUTER_FALLBACK_MODEL",
    ]
)
def test_production_settings_require_explicit_pinned_openrouter_models(
    tmp_path: Path, name: str
) -> None:
    env = _environment(tmp_path)
    env.pop(name)
    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)


def test_production_settings_require_openrouter_server_secret(tmp_path: Path) -> None:
    env = _environment(tmp_path)
    env["OPENROUTER_API_KEY"] = " "
    with pytest.raises(ProductionConfigurationError, match="OPENROUTER_API_KEY"):
        load_production_settings(env)
