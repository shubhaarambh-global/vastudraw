from __future__ import annotations

from pathlib import Path

from tests.production.test_settings import base_environment

from ai_vastu.production.settings import load_production_settings


def test_legacy_gemini_configuration_cannot_activate_production(
    tmp_path: Path,
) -> None:
    environment = base_environment(tmp_path)
    environment.update(
        {
            "GEMINI_API_KEY": "legacy-gemini-secret",
            "AI_VASTU_GEMINI_MODEL": "gemini-3.1-flash-lite",
        }
    )

    settings = load_production_settings(environment)

    assert settings.plan_recognition_provider == "nvidia_nim"
    assert "legacy-gemini-secret" not in str(settings.redacted_summary())
