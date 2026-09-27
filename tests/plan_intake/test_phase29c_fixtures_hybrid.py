from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import httpx
import pytest

from ai_vastu.generation_intake import (
    GenerationIntakeError,
    GenerationIntakeStore,
    IncomingGenerationAttachment,
)
from ai_vastu.openrouter_http import (
    OpenRouterClient,
    OpenRouterModelPolicy,
    OpenRouterRequestError,
)
from ai_vastu.plan_intake import (
    PlanIntakeService,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
)
from ai_vastu.plan_intake.errors import (
    PlanIntakeConfigurationError,
    PlanIntakeProviderError,
)
from ai_vastu.plan_intake.provider import GeminiPlanRecognitionProvider
from ai_vastu.plan_intake.service import create_plan_recognition_provider
from ai_vastu.requirements.errors import RequirementsConfigurationError
from ai_vastu.requirements.providers.openrouter_chat import OpenRouterRequirementsProvider
from ai_vastu.requirements.service import create_provider

FIXTURE_PATH = (
    Path(__file__).parents[1] / "fixtures" / "phase29c" / "hybrid_provider_cases.json"
)
PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
INTAKE_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture(scope="module")
def provider_cases() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8")),
    )


def _upload(provider_cases: dict[str, Any], case: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        next(item for item in provider_cases["uploads"] if item["case"] == case),
    )


def _blob(item: dict[str, Any]) -> PlanReferenceBlob:
    return PlanReferenceBlob(
        filename=item["filename"],
        content_type=item["content_type"],
        kind=PlanReferenceKind(item["kind"]),
        data=base64.b64decode(item["base64"], validate=True),
    )


def test_fixture_catalog_is_complete_deterministic_and_secret_free(
    provider_cases: dict[str, Any],
) -> None:
    assert set(provider_cases["openrouter"]) == {
        "valid",
        "timeout",
        "rate_limited",
        "server_errors",
        "invalid_json",
        "unexpected_schema",
        "empty_content",
        "invalid_model",
    }
    assert set(provider_cases["gemini"]) == {
        "valid_response",
        "malformed_output",
        "missing_fields",
        "timeout",
        "rate_limited",
        "server_error",
    }
    assert {item["case"] for item in provider_cases["uploads"]} == {
        "valid_jpg",
        "valid_png",
        "valid_pdf",
        "corrupt_image",
        "corrupt_pdf",
        "unsupported_mime",
        "unsupported_extension",
    }
    serialized = json.dumps(provider_cases).lower()
    assert "sk-" not in serialized
    assert "AIza".lower() not in serialized
    assert "bearer " not in serialized


def test_openrouter_valid_response_fixture_passes_schema_validation(
    provider_cases: dict[str, Any],
) -> None:
    fixture = provider_cases["openrouter"]["valid"]

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            fixture["status"],
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": fixture["content"]}}
                ]
            },
        )

    result = OpenRouterClient(
        api_key="fixture-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "Return JSON."},),
        models=OpenRouterModelPolicy().reasoning_chain,
        validator=lambda payload, _model: payload["ok"],
        temperature=0.0,
    )

    assert result is True


@pytest.mark.parametrize(
    "case",
    ("invalid_json", "unexpected_schema", "empty_content"),
)
def test_openrouter_invalid_response_fixtures_exhaust_only_approved_chain(
    provider_cases: dict[str, Any],
    case: str,
) -> None:
    fixture = provider_cases["openrouter"][case]
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            fixture["status"],
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": fixture["content"]}}
                ]
            },
        )

    with pytest.raises(OpenRouterRequestError, match="invalid_response"):
        OpenRouterClient(
            api_key="fixture-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "Return JSON."},),
            models=OpenRouterModelPolicy().reasoning_chain,
            validator=lambda payload, _model: payload["ok"],
            temperature=0.0,
        )

    assert calls == 2


@pytest.mark.parametrize("case", ("valid_jpg", "valid_png", "valid_pdf"))
def test_direct_gemini_recognizes_qualified_reference_types_from_fixture(
    provider_cases: dict[str, Any],
    tmp_path: Path,
    case: str,
) -> None:
    item = _upload(provider_cases, case)
    reference = _blob(item)
    GenerationIntakeStore(tmp_path / case).create(
        PROJECT_ID,
        "Validate the upload boundary before provider recognition.",
        (
            IncomingGenerationAttachment(
                original_filename=item["filename"],
                media_type=item["content_type"],
                content=reference.data,
            ),
        ),
        intake_id=INTAKE_ID,
    )
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        body = json.loads(request.content)
        inline = body["contents"][0]["parts"][1]["inlineData"]
        assert inline["mimeType"] == item["content_type"]
        assert base64.b64decode(inline["data"], validate=True) == reference.data
        response_text = json.dumps(provider_cases["gemini"]["valid_response"])
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": response_text}]}}]},
        )

    provider = GeminiPlanRecognitionProvider(
        api_key="fixture-key",
        model="gemini-3.1-flash-lite",
        transport=httpx.MockTransport(handler),
    )
    result = PlanIntakeService(provider).recognize(
        PlanRecognitionInput(
            project_id=PROJECT_ID,
            intake_id=INTAKE_ID,
            prompt="Recognize this plan without authoring canonical geometry.",
            references=(reference,),
        )
    )

    assert calls == 1
    assert result.provider == "gemini"
    assert result.model == "gemini-3.1-flash-lite"
    assert result.envelope.requires_confirmation is True
    assert result.orientation.requires_confirmation is True


@pytest.mark.parametrize("case", ("corrupt_image", "corrupt_pdf"))
def test_corrupt_upload_fixtures_fail_before_provider_call(
    provider_cases: dict[str, Any],
    tmp_path: Path,
    case: str,
) -> None:
    item = _upload(provider_cases, case)
    store = GenerationIntakeStore(tmp_path / case)

    with pytest.raises(GenerationIntakeError, match="signature"):
        store.create(
            PROJECT_ID,
            "Recognize the supplied plan.",
            (
                IncomingGenerationAttachment(
                    original_filename=item["filename"],
                    media_type=item["content_type"],
                    content=base64.b64decode(item["base64"], validate=True),
                ),
            ),
            intake_id=INTAKE_ID,
        )


@pytest.mark.parametrize("case", ("unsupported_mime", "unsupported_extension"))
def test_unsupported_upload_fixtures_fail_before_provider_call(
    provider_cases: dict[str, Any],
    tmp_path: Path,
    case: str,
) -> None:
    item = _upload(provider_cases, case)
    store = GenerationIntakeStore(tmp_path / case)

    with pytest.raises(GenerationIntakeError, match="supported"):
        store.create(
            PROJECT_ID,
            "Recognize the supplied plan.",
            (
                IncomingGenerationAttachment(
                    original_filename=item["filename"],
                    media_type=item["content_type"],
                    content=base64.b64decode(item["base64"], validate=True),
                ),
            ),
            intake_id=INTAKE_ID,
        )


@pytest.mark.parametrize("response_case", ("malformed_output", "missing_fields"))
def test_malformed_gemini_fixture_fails_closed_without_retry(
    provider_cases: dict[str, Any],
    response_case: str,
) -> None:
    item = _upload(provider_cases, "valid_png")
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        fixture = provider_cases["gemini"][response_case]
        text = fixture if isinstance(fixture, str) else json.dumps(fixture)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
        )

    provider = GeminiPlanRecognitionProvider(
        api_key="fixture-key",
        model="gemini-3.1-flash-lite",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(PlanIntakeProviderError):
        provider.recognize(
            PlanRecognitionInput(
                project_id=PROJECT_ID,
                intake_id=INTAKE_ID,
                prompt="Recognize plan.",
                references=(_blob(item),),
            )
        )

    assert calls == 1


def test_hybrid_factories_route_text_to_openrouter_and_plan_to_direct_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PROVIDER", "openrouter")
    monkeypatch.setenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "gemini")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-openrouter-key")
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-gemini-key")

    assert isinstance(create_provider(), OpenRouterRequirementsProvider)
    assert isinstance(create_plan_recognition_provider(), GeminiPlanRecognitionProvider)


def test_missing_hybrid_credentials_do_not_cross_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PROVIDER", "openrouter")
    monkeypatch.setenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "gemini")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-gemini-key")

    with pytest.raises(RequirementsConfigurationError):
        create_provider()

    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-openrouter-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(PlanIntakeConfigurationError):
        create_plan_recognition_provider()
