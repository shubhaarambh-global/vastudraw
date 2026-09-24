from pathlib import Path

import pytest
from tests.production.test_settings import base_environment

from ai_vastu.production.settings import (
    ProductionConfigurationError,
    load_production_settings,
)


def _base_environment(tmp_path: Path) -> dict[str, str]:
    return base_environment(tmp_path)


def test_production_settings_accept_direct_gemini_plan_vision(tmp_path: Path) -> None:
    settings = load_production_settings(_base_environment(tmp_path))

    assert settings.requirements_provider == "openrouter"
    assert settings.plan_recognition_provider == "gemini"
    assert settings.gemini_model == "gemini-3.1-flash-lite"
    assert settings.openai_model is None


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "openrouter"),
        ("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "fixture"),
        ("AI_VASTU_PLAN_RECOGNITION_MODEL", "gemini-2.5-flash"),
        ("AI_VASTU_GEMINI_MODEL", "gemini-2.5-flash"),
        ("GEMINI_API_KEY", ""),
    ],
)
def test_production_settings_reject_gemini_vision_drift(
    tmp_path: Path, name: str, value: str
) -> None:
    env = _base_environment(tmp_path)
    env[name] = value
    with pytest.raises(ProductionConfigurationError, match=name):
        load_production_settings(env)
