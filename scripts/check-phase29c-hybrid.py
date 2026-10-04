from __future__ import annotations

import io
import json
import os
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import httpx
from reportlab.pdfgen import canvas

from ai_vastu.nvidia_nim_http import NvidiaNimClient, NvidiaNimModelPolicy
from ai_vastu.plan_intake import (
    PlanIntakeService,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
)
from ai_vastu.plan_intake.nvidia_nim_provider import NvidiaNimPlanRecognitionProvider
from ai_vastu.plan_intake.provider import FixturePlanRecognitionProvider
from ai_vastu.production.settings import load_production_settings
from ai_vastu.requirements.providers import FixtureRequirementsProvider, InterpretationInput
from ai_vastu.requirements.providers.nvidia_nim import NvidiaNimRequirementsProvider
from ai_vastu.requirements.service import create_provider

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
DRAFT_ID = UUID("33333333-3333-3333-3333-333333333333")
INTAKE_ID = UUID("44444444-4444-4444-4444-444444444444")
SECRET = "offline-nvidia-placeholder"


def _environment() -> dict[str, str]:
    durable_root = (ROOT / ".local" / "phase29c-nvidia-offline").resolve()
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
        "AI_VASTU_REQUIREMENTS_PROVIDER": "nvidia_nim",
        "AI_VASTU_ARCHITECT_PROVIDER": "nvidia_nim",
        "AI_VASTU_VASTU_PROVIDER": "nvidia_nim",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER": "nvidia_nim",
        "AI_VASTU_REVISION_PROVIDER": "nvidia_nim",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER": "nvidia_nim",
        "AI_VASTU_NVIDIA_BASE_URL": "https://integrate.api.nvidia.com/v1",
        "AI_VASTU_NVIDIA_PRIMARY_MODEL": "nvidia/nemotron-3-ultra-550b-a55b",
        "AI_VASTU_NVIDIA_VISION_MODEL": (
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
        ),
        "NVIDIA_API_KEY": SECRET,
    }


def _response(payload: dict[str, object], model: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": model,
            "choices": [{"message": {"content": json.dumps(payload)}}],
        },
    )


def _requirements_probe(environment: dict[str, str]) -> None:
    request = InterpretationInput(
        draft_id=DRAFT_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        prompt="30 x 50 ft, north road, two bedrooms and one-car parking.",
        references=(),
    )
    payload = FixtureRequirementsProvider().interpret(request).model_dump(
        mode="json",
        exclude={
            "draft_id", "user_id", "project_id", "prompt", "reference_names",
            "provider", "model",
        },
    )
    provider = NvidiaNimRequirementsProvider(
        client=NvidiaNimClient.from_environment(
            environment,
            transport=httpx.MockTransport(
                lambda request: _response(
                    payload,
                    str(json.loads(request.content)["model"]),
                )
            ),
        ),
        policy=NvidiaNimModelPolicy.from_environment(environment),
    )
    with patch.object(
        NvidiaNimRequirementsProvider, "from_environment", return_value=provider
    ):
        selected = create_provider()
        draft = selected.interpret(request)
    if selected.name != "nvidia_nim" or draft.provider != "nvidia_nim":
        raise RuntimeError("NVIDIA requirements factory isolation failed.")
    if draft.model != NvidiaNimModelPolicy().primary:
        raise RuntimeError("NVIDIA primary model pin was not preserved.")


def _pdf_bytes() -> bytes:
    output = io.BytesIO()
    document = canvas.Canvas(output, pagesize=(320, 400), invariant=True)
    document.drawString(120, 380, "NORTH")
    document.rect(30, 30, 260, 330)
    document.drawString(60, 250, "LIVING")
    document.showPage()
    document.save()
    return output.getvalue()


def _plan_probe(environment: dict[str, str]) -> None:
    fixture_request = PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="Synthetic qualification plan. Preserve uncertainty.",
        references=(),
    )
    payload = FixturePlanRecognitionProvider().recognize(fixture_request).model_dump(
        mode="json",
        exclude={
            "project_id", "intake_id", "provider", "model", "reference_names",
            "content_hash",
        },
    )
    provider = NvidiaNimPlanRecognitionProvider(
        client=NvidiaNimClient.from_environment(
            environment,
            transport=httpx.MockTransport(
                lambda request: _response(
                    payload,
                    str(json.loads(request.content)["model"]),
                )
            ),
        ),
        policy=NvidiaNimModelPolicy.from_environment(environment),
    )
    draft = PlanIntakeService(provider).recognize(
        PlanRecognitionInput(
            project_id=fixture_request.project_id,
            intake_id=fixture_request.intake_id,
            prompt=fixture_request.prompt,
            references=(
                PlanReferenceBlob(
                    filename="synthetic-plan.pdf",
                    content_type="application/pdf",
                    kind=PlanReferenceKind.PDF,
                    data=_pdf_bytes(),
                ),
            ),
        )
    )
    if draft.provider != "nvidia_nim" or draft.model != NvidiaNimModelPolicy().vision:
        raise RuntimeError("NVIDIA plan-recognition pin was not preserved.")
    if (
        not draft.envelope.requires_confirmation
        or not draft.orientation.requires_confirmation
        or any(not room.requires_confirmation for room in draft.rooms)
    ):
        raise RuntimeError("Plan observations must remain confirmation-required.")
    if draft.content_hash != draft.compute_content_hash():
        raise RuntimeError("Plan recognition content hash is invalid.")


def main() -> None:
    environment = _environment()
    summary = str(load_production_settings(environment).redacted_summary())
    if SECRET in summary:
        raise RuntimeError("Production settings exposed NVIDIA_API_KEY.")
    if "OPENROUTER_API_KEY" in environment or "GEMINI_API_KEY" in environment:
        raise RuntimeError("Legacy credentials entered the NVIDIA profile.")
    with patch.dict(os.environ, environment, clear=False):
        _requirements_probe(environment)
        _plan_probe(environment)
    print(
        "PHASE29C NVIDIA_NIM PASS_LOCAL: factories=true, pdf_local=true, "
        "network_calls=false, secrets_redacted=true"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"PHASE29C NVIDIA_NIM FAIL ({type(exc).__name__})") from None
