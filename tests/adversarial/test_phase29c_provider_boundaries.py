from __future__ import annotations

import asyncio
import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from ai_vastu.generation_intake import (
    GenerationIntakeError,
    GenerationIntakeStore,
    IncomingGenerationAttachment,
)
from ai_vastu.openrouter_http import (
    FALLBACK_REASONING_MODEL,
    PRIMARY_ARCHITECTURAL_MODEL,
    VISION_PLAN_MODEL,
    OpenRouterClient,
    OpenRouterModelPolicy,
    OpenRouterRequestError,
)
from ai_vastu.plan_intake import (
    PlanEnvelopeObservation,
    PlanIntakeService,
    PlanObservationSource,
    PlanOrientationObservation,
    PlanRecognitionDraft,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
    PlanRoomObservation,
)
from ai_vastu.plan_intake.errors import (
    PlanIntakeConfigurationError,
    PlanIntakeProviderError,
)
from ai_vastu.plan_intake.provider import GeminiPlanRecognitionProvider
from ai_vastu.plan_intake.service import create_plan_recognition_provider
from ai_vastu.production.settings import (
    ProductionConfigurationError,
    load_production_settings,
)
from ai_vastu.provider_runtime import ProviderFailureCategory
from ai_vastu.requirements.errors import RequirementsConfigurationError
from ai_vastu.requirements.service import create_provider as create_requirements_provider
from app.requirements_routes import _MAX_FILE_BYTES, _read_references

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
INTAKE_ID = UUID("22222222-2222-2222-2222-222222222222")
SENTINEL_SECRET = "phase29c-never-leak-secret"


def _openrouter_call(
    transport: httpx.BaseTransport,
    models: tuple[str, ...],
) -> object:
    return OpenRouterClient(
        api_key=SENTINEL_SECRET,
        transport=transport,
    ).complete_validated_json(
        messages=({"role": "user", "content": "private client prompt"},),
        models=models,
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )


def _production_environment(tmp_path: Path) -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "AI_VASTU_AUTH_MODE": "supabase",
        "AI_VASTU_DATABASE_URL": "postgresql://user:pass@db.example.com/vastu",
        "AI_VASTU_SUPABASE_URL": "https://example.supabase.co",
        "AI_VASTU_SUPABASE_JWT_AUDIENCE": "authenticated",
        "AI_VASTU_WEB_ORIGINS": "https://app.example.com",
        "AI_VASTU_TRUSTED_HOSTS": "api.example.com",
        "AI_VASTU_REQUIREMENTS_PATH": str((tmp_path / "requirements").resolve()),
        "AI_VASTU_GENERATION_UPLOAD_ROOT": str((tmp_path / "uploads").resolve()),
        "AI_VASTU_PAYMENT_GATEWAY": "phonepe",
        "AI_VASTU_REQUIREMENTS_PROVIDER": "openrouter",
        "AI_VASTU_ARCHITECT_PROVIDER": "openrouter",
        "AI_VASTU_VASTU_PROVIDER": "openrouter",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER": "openrouter",
        "AI_VASTU_REVISION_PROVIDER": "openrouter",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER": "gemini",
        "AI_VASTU_PLAN_RECOGNITION_MODEL": "gemini-3.1-flash-lite",
        "AI_VASTU_GEMINI_MODEL": "gemini-3.1-flash-lite",
        "AI_VASTU_OPENROUTER_PRIMARY_MODEL": PRIMARY_ARCHITECTURAL_MODEL,
        "AI_VASTU_OPENROUTER_VISION_MODEL": VISION_PLAN_MODEL,
        "AI_VASTU_OPENROUTER_FALLBACK_MODEL": FALLBACK_REASONING_MODEL,
        "OPENROUTER_API_KEY": "offline-openrouter-placeholder",
        "GEMINI_API_KEY": "offline-gemini-placeholder",
    }


def test_frontend_sources_cannot_reference_server_provider_keys() -> None:
    forbidden = ("OPENROUTER_API_KEY", "GEMINI_API_KEY")
    frontend_root = REPOSITORY_ROOT / "apps" / "web"
    examined = 0

    for path in frontend_root.rglob("*"):
        if not path.is_file() or "node_modules" in path.parts or ".next" in path.parts:
            continue
        if path.suffix.lower() not in {".js", ".jsx", ".mjs", ".ts", ".tsx", ".json"}:
            continue
        examined += 1
        text = path.read_text(encoding="utf-8")
        assert all(name not in text for name in forbidden), path

    assert examined > 0
    example = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "NEXT_PUBLIC_OPENROUTER" not in example
    assert "NEXT_PUBLIC_GEMINI" not in example


def test_openrouter_auth_failure_does_not_fallback_or_leak_response() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(
            401,
            json={"error": f"bad key {SENTINEL_SECRET}; private client prompt"},
        )

    with pytest.raises(OpenRouterRequestError) as captured:
        _openrouter_call(
            httpx.MockTransport(handler),
            OpenRouterModelPolicy().reasoning_chain,
        )

    assert captured.value.category is ProviderFailureCategory.AUTHENTICATION
    assert calls == [PRIMARY_ARCHITECTURAL_MODEL]
    assert SENTINEL_SECRET not in str(captured.value)
    assert "private client prompt" not in str(captured.value)


def test_openrouter_outage_uses_only_the_pinned_free_fallback_once() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(503, text=f"upstream dumped {SENTINEL_SECRET}")

    with pytest.raises(OpenRouterRequestError) as captured:
        _openrouter_call(
            httpx.MockTransport(handler),
            OpenRouterModelPolicy().reasoning_chain,
        )

    assert captured.value.category is ProviderFailureCategory.UNAVAILABLE
    assert calls == [PRIMARY_ARCHITECTURAL_MODEL, FALLBACK_REASONING_MODEL]
    assert all(model.endswith(":free") for model in calls)
    assert SENTINEL_SECRET not in str(captured.value)


def test_gemini_malformed_output_fails_once_without_leaking_payload() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        "not-json private client prompt "
                                        f"{SENTINEL_SECRET}"
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    provider = GeminiPlanRecognitionProvider(
        api_key=SENTINEL_SECRET,
        model="gemini-3.1-flash-lite",
        transport=httpx.MockTransport(handler),
    )
    request = PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="private client prompt",
        references=(
            PlanReferenceBlob(
                filename="plan.png",
                content_type="image/png",
                kind=PlanReferenceKind.IMAGE,
                data=b"\x89PNG\r\n\x1a\nfixture",
            ),
        ),
    )

    with pytest.raises(PlanIntakeProviderError) as captured:
        provider.recognize(request)

    assert calls == 1
    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert SENTINEL_SECRET not in str(captured.value)
    assert "private client prompt" not in str(captured.value)


def test_gemini_outage_retries_once_without_cross_provider_fallback() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host or "")
        return httpx.Response(503, text=f"provider body {SENTINEL_SECRET}")

    provider = GeminiPlanRecognitionProvider(
        api_key=SENTINEL_SECRET,
        model="gemini-3.1-flash-lite",
        transport=httpx.MockTransport(handler),
    )
    request = PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="private client prompt",
        references=(),
    )

    with pytest.raises(PlanIntakeProviderError) as captured:
        provider.recognize(request)

    assert captured.value.category is ProviderFailureCategory.UNAVAILABLE
    assert calls == [
        "generativelanguage.googleapis.com",
        "generativelanguage.googleapis.com",
    ]
    assert SENTINEL_SECRET not in str(captured.value)


class _HostileVisualProvider:
    name = "gemini"

    def recognize(self, request: PlanRecognitionInput) -> PlanRecognitionDraft:
        return PlanRecognitionDraft(
            project_id=request.project_id,
            intake_id=request.intake_id,
            provider=self.name,
            model="hostile-model",
            reference_names=("plan.png",),
            envelope=PlanEnvelopeObservation(
                geometry_type="RECTANGLE",
                width_mm=9_000,
                depth_mm=12_000,
                source=PlanObservationSource.USER_CONFIRMED,
                requires_confirmation=False,
            ),
            orientation=PlanOrientationObservation(
                north_rotation_deg=0,
                source=PlanObservationSource.USER_CONFIRMED,
                requires_confirmation=False,
            ),
            rooms=(
                PlanRoomObservation(
                    room_type="living",
                    source=PlanObservationSource.USER_CONFIRMED,
                    requires_confirmation=False,
                ),
            ),
        ).with_content_hash()


def test_hostile_visual_payload_cannot_claim_user_confirmation() -> None:
    request = PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="Analyze only; do not author geometry.",
        references=(
            PlanReferenceBlob(
                filename="plan.png",
                content_type="image/png",
                kind=PlanReferenceKind.IMAGE,
                data=b"\x89PNG\r\n\x1a\nfixture",
            ),
        ),
    )

    result = PlanIntakeService(_HostileVisualProvider()).recognize(request)

    assert result.envelope.source is PlanObservationSource.IMAGE
    assert result.orientation.source is PlanObservationSource.IMAGE
    assert result.rooms[0].source is PlanObservationSource.IMAGE
    assert result.envelope.requires_confirmation is True
    assert result.orientation.requires_confirmation is True
    assert result.rooms[0].requires_confirmation is True
    assert result.content_hash == result.compute_content_hash()


def test_oversized_requirements_upload_is_rejected_before_interpretation() -> None:
    upload = UploadFile(
        BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * _MAX_FILE_BYTES),
        filename="oversized.png",
        headers=Headers({"content-type": "image/png"}),
    )

    with pytest.raises(HTTPException) as captured:
        asyncio.run(_read_references([upload]))

    assert captured.value.status_code == 413
    assert captured.value.detail == "Reference file too large."


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("payload.exe", "image/png", b"\x89PNG\r\n\x1a\npng"),
        ("spoof.png", "image/jpeg", b"\xff\xd8\xffjpeg"),
        ("spoof.jpg", "application/pdf", b"%PDF-1.7\nfixture"),
    ],
)
def test_requirements_upload_rejects_extension_mime_confusion(
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    upload = UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )

    with pytest.raises(HTTPException) as captured:
        asyncio.run(_read_references([upload]))

    assert captured.value.status_code == 415
    assert captured.value.detail == "Unsupported reference type."


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("truncated.jpg", "image/jpeg", b"\xff\xd8\xff"),
        ("truncated.png", "image/png", b"\x89PNG\r\n\x1a\n"),
        ("truncated.pdf", "application/pdf", b"%PDF-"),
    ],
)
def test_requirements_upload_rejects_truncated_magic_only_content(
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    upload = UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )

    with pytest.raises(HTTPException) as captured:
        asyncio.run(_read_references([upload]))

    assert captured.value.status_code == 422


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("spoof.png", "image/jpeg", b"\xff\xd8\xffjpeg"),
        ("spoof.jpg", "image/jpeg", b"\x89PNG\r\n\x1a\npng"),
        ("spoof.pdf", "image/png", b"%PDF-1.7\nfixture"),
    ],
)
def test_generation_upload_rejects_mime_extension_or_signature_confusion(
    tmp_path: Path,
    filename: str,
    content_type: str,
    content: bytes,
) -> None:
    store = GenerationIntakeStore(tmp_path / filename.replace(".", "-"))

    with pytest.raises(GenerationIntakeError):
        store.create(
            PROJECT_ID,
            "Analyze this untrusted plan reference.",
            (IncomingGenerationAttachment(filename, content_type, content),),
        )


def test_missing_provider_credentials_do_not_cross_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PROVIDER", "openrouter")
    monkeypatch.setenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "gemini")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "offline-gemini-placeholder")

    with pytest.raises(RequirementsConfigurationError) as openrouter_failure:
        create_requirements_provider()
    assert "offline-gemini-placeholder" not in str(openrouter_failure.value)

    monkeypatch.setenv("OPENROUTER_API_KEY", "offline-openrouter-placeholder")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(PlanIntakeConfigurationError) as gemini_failure:
        create_plan_recognition_provider()
    assert "offline-openrouter-placeholder" not in str(gemini_failure.value)

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RequirementsConfigurationError):
        create_requirements_provider()
    with pytest.raises(PlanIntakeConfigurationError):
        create_plan_recognition_provider()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AI_VASTU_REQUIREMENTS_PROVIDER", "fixture"),
        ("AI_VASTU_ARCHITECT_PROVIDER", "gemini"),
        ("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "openrouter"),
        ("AI_VASTU_PLAN_RECOGNITION_MODEL", "gemini-latest"),
        ("OPENROUTER_API_KEY", ""),
        ("GEMINI_API_KEY", ""),
    ],
)
def test_production_rejects_dev_or_cross_provider_confusion(
    tmp_path: Path,
    name: str,
    value: str,
) -> None:
    environment = _production_environment(tmp_path)
    environment[name] = value

    with pytest.raises(ProductionConfigurationError):
        load_production_settings(environment)


def test_production_summary_never_contains_provider_credentials(tmp_path: Path) -> None:
    environment = _production_environment(tmp_path)
    environment["OPENROUTER_API_KEY"] = f"openrouter-{SENTINEL_SECRET}"
    environment["GEMINI_API_KEY"] = f"gemini-{SENTINEL_SECRET}"

    summary = json.dumps(load_production_settings(environment).redacted_summary())

    assert SENTINEL_SECRET not in summary
    assert "OPENROUTER_API_KEY" not in summary
    assert "GEMINI_API_KEY" not in summary


def test_provider_runtime_failures_do_not_echo_hostile_provider_names() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            f"connection failed with {SENTINEL_SECRET}",
            request=request,
        )

    with pytest.raises(OpenRouterRequestError) as captured:
        _openrouter_call(
            httpx.MockTransport(handler),
            OpenRouterModelPolicy().reasoning_chain,
        )

    assert captured.value.category is ProviderFailureCategory.UNAVAILABLE
    assert SENTINEL_SECRET not in str(captured.value)
