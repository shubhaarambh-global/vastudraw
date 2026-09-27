from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import httpx

from ai_vastu.openrouter_http import (
    FALLBACK_REASONING_MODEL,
    PRIMARY_ARCHITECTURAL_MODEL,
    VISION_PLAN_MODEL,
)
from ai_vastu.plan_intake import (
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
)
from ai_vastu.plan_intake.provider import (
    FixturePlanRecognitionProvider,
    GeminiPlanRecognitionProvider,
)
from ai_vastu.plan_intake.service import create_plan_recognition_provider
from ai_vastu.production.settings import load_production_settings
from ai_vastu.requirements.providers import (
    FixtureRequirementsProvider,
    InterpretationInput,
    OpenRouterRequirementsProvider,
)
from ai_vastu.requirements.providers.openrouter_chat import (
    build_openrouter_requirements_provider_for_test,
)
from ai_vastu.requirements.service import create_provider

ROOT = Path(__file__).resolve().parents[1]
GEMINI_MODEL = "gemini-3.1-flash-lite"
PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = UUID("33333333-3333-3333-3333-333333333333")
INTAKE_ID = UUID("44444444-4444-4444-4444-444444444444")


def _production_environment() -> dict[str, str]:
    durable_root = (ROOT / ".local" / "phase29c-offline").resolve()
    return {
        "APP_ENV": "production",
        "AI_VASTU_AUTH_MODE": "supabase",
        "AI_VASTU_DATABASE_URL": "postgresql://offline@db.example.test/vastu",
        "AI_VASTU_SUPABASE_URL": "https://example.supabase.co",
        "AI_VASTU_SUPABASE_JWT_AUDIENCE": "authenticated",
        "AI_VASTU_WEB_ORIGINS": "https://app.example.test",
        "AI_VASTU_TRUSTED_HOSTS": "api.example.test",
        "AI_VASTU_REQUIREMENTS_PATH": str(durable_root / "requirements"),
        "AI_VASTU_GENERATION_UPLOAD_ROOT": str(durable_root / "uploads"),
        "AI_VASTU_PAYMENT_GATEWAY": "disabled",
        "AI_VASTU_REQUIREMENTS_PROVIDER": "openrouter",
        "AI_VASTU_ARCHITECT_PROVIDER": "openrouter",
        "AI_VASTU_VASTU_PROVIDER": "openrouter",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER": "openrouter",
        "AI_VASTU_REVISION_PROVIDER": "openrouter",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER": "gemini",
        "AI_VASTU_PLAN_RECOGNITION_MODEL": GEMINI_MODEL,
        "AI_VASTU_GEMINI_MODEL": GEMINI_MODEL,
        "AI_VASTU_OPENROUTER_PRIMARY_MODEL": PRIMARY_ARCHITECTURAL_MODEL,
        "AI_VASTU_OPENROUTER_VISION_MODEL": VISION_PLAN_MODEL,
        "AI_VASTU_OPENROUTER_FALLBACK_MODEL": FALLBACK_REASONING_MODEL,
        "AI_VASTU_OPENROUTER_ATTEMPT_TIMEOUT_SECONDS": "120",
        "AI_VASTU_OPENROUTER_TOTAL_TIMEOUT_SECONDS": "240",
        "AI_VASTU_OPENROUTER_RETRY_DELAY_SECONDS": "0",
        "AI_VASTU_OPENROUTER_MAX_RETRY_AFTER_SECONDS": "0",
        "AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS": "90",
        "AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS": "181",
        "AI_VASTU_GEMINI_RETRY_DELAY_SECONDS": "1",
        "AI_VASTU_GEMINI_MAX_RETRY_AFTER_SECONDS": "5",
        "OPENROUTER_API_KEY": "offline-openrouter-placeholder",
        "GEMINI_API_KEY": "offline-gemini-placeholder",
    }


def _requirements_probe() -> None:
    request = InterpretationInput(
        draft_id=DRAFT_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        prompt="30 x 50 ft, north road, two bedrooms and one-car parking.",
        references=(),
    )
    response_payload = FixtureRequirementsProvider().interpret(request).model_dump(
        mode="json"
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps(response_payload)}}
                ]
            },
        )

    provider = build_openrouter_requirements_provider_for_test(
        api_key="offline-openrouter-placeholder",
        transport=httpx.MockTransport(handler),
    )
    with patch.object(
        OpenRouterRequirementsProvider,
        "from_environment",
        return_value=provider,
    ):
        selected = create_provider()
        draft = selected.interpret(request)

    if selected.name != "openrouter" or draft.provider != "openrouter":
        raise RuntimeError("OpenRouter requirements factory isolation failed.")
    if draft.model != PRIMARY_ARCHITECTURAL_MODEL:
        raise RuntimeError("OpenRouter requirements model pin was not preserved.")


def _plan_probe() -> None:
    request = PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="Synthetic north-up plan used only for an offline factory probe.",
        references=(
            PlanReferenceBlob(
                filename="synthetic-plan.png",
                content_type="image/png",
                kind=PlanReferenceKind.IMAGE,
                data=b"synthetic-plan-bytes",
            ),
        ),
    )
    fixture = FixturePlanRecognitionProvider().recognize(request)
    response_payload = fixture.model_dump(
        mode="json",
        exclude={
            "project_id",
            "intake_id",
            "provider",
            "model",
            "reference_names",
            "content_hash",
        },
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps(response_payload)}]
                        }
                    }
                ]
            },
        )

    provider = GeminiPlanRecognitionProvider(
        "offline-gemini-placeholder",
        GEMINI_MODEL,
        transport=httpx.MockTransport(handler),
    )
    with patch.object(
        GeminiPlanRecognitionProvider,
        "from_environment",
        return_value=provider,
    ):
        selected = create_plan_recognition_provider()
        draft = selected.recognize(request)

    if selected.name != "gemini" or draft.provider != "gemini":
        raise RuntimeError("Gemini plan-recognition factory isolation failed.")
    if (
        not draft.envelope.requires_confirmation
        or not draft.orientation.requires_confirmation
        or any(not room.requires_confirmation for room in draft.rooms)
    ):
        raise RuntimeError("Plan observations must require confirmation.")


def main() -> None:
    environment = _production_environment()
    settings = load_production_settings(environment)
    summary = str(settings.redacted_summary())
    if "offline-openrouter-placeholder" in summary or "offline-gemini-placeholder" in summary:
        raise RuntimeError("Production settings summary exposed a provider credential.")

    with patch.dict(os.environ, environment, clear=False):
        _requirements_probe()
        _plan_probe()

    print(
        "PHASE29C_OFFLINE PASS: factories=true, synthetic_only=true, "
        "network_calls=false, secrets_redacted=true"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"PHASE29C_OFFLINE FAIL ({type(exc).__name__})") from None
