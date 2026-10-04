from __future__ import annotations

import base64
import io
from typing import Any, cast
from uuid import UUID

import pytest
from PIL import Image

from ai_vastu.nvidia_nim_http import VISION_MODEL, NvidiaNimModelPolicy
from ai_vastu.pdf_render_adapter import PdfRenderError, RenderedPdfPage
from ai_vastu.plan_intake import (
    NvidiaNimPlanRecognitionProvider,
    PlanIntakeService,
    PlanObservationSource,
    PlanRecognitionDraft,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
)
from ai_vastu.plan_intake.errors import PlanIntakeProviderError
from ai_vastu.plan_intake.service import create_plan_recognition_provider

PROJECT_ID = UUID("71000000-0000-0000-0000-00000000029c")
INTAKE_ID = UUID("72000000-0000-0000-0000-00000000029c")


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def complete_validated_json(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        parsed = {
            "envelope": {
                "geometry_type": "RECTANGLE",
                "width_mm": 9000,
                "depth_mm": 12000,
                "confidence": 0.9,
                "source": "USER_CONFIRMED",
                "requires_confirmation": False,
            },
            "orientation": {
                "north_rotation_deg": 0,
                "confidence": 0.8,
                "source": "USER_CONFIRMED",
                "requires_confirmation": False,
            },
            "rooms": [
                {
                    "room_type": "living",
                    "confidence": 0.8,
                    "source": "USER_CONFIRMED",
                    "requires_confirmation": False,
                }
            ],
            "observations": ["advisory recognition"],
            "questions": [],
            "warnings": [],
        }
        return kwargs["validator"](parsed, kwargs["models"][0])


class StubPdfRenderer:
    def render(self, *, filename: str, data: bytes) -> tuple[RenderedPdfPage, ...]:
        assert filename == "floor-plan.pdf"
        assert data == b"raw-pdf-must-stay-local"
        return (
            RenderedPdfPage(
                page_number=1,
                filename="floor-plan.pdf#page-1.png",
                content_type="image/png",
                data=b"rendered-page-png",
            ),
        )


class FailingPdfRenderer:
    def render(self, *, filename: str, data: bytes) -> tuple[RenderedPdfPage, ...]:
        raise PdfRenderError("sensitive parser detail")


def _provider(
    client: RecordingClient,
    *,
    pdf_renderer: object | None = None,
) -> NvidiaNimPlanRecognitionProvider:
    return NvidiaNimPlanRecognitionProvider(
        client=cast(Any, client),
        policy=NvidiaNimModelPolicy(),
        pdf_renderer=cast(Any, pdf_renderer),
    )


def _request(reference: PlanReferenceBlob) -> PlanRecognitionInput:
    return PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="Recognize this plan without authoring geometry.",
        references=(reference,),
    )


def _image_bytes(format_name: str) -> bytes:
    image = Image.new("RGB", (12, 8), "white")
    output = io.BytesIO()
    image.save(output, format=format_name)
    image.close()
    return output.getvalue()


@pytest.mark.parametrize(
    ("content_type", "format_name"),
    [("image/png", "PNG"), ("image/jpeg", "JPEG")],
)
def test_nvidia_vision_accepts_png_and_jpeg_with_confirmation_boundary(
    content_type: str,
    format_name: str,
) -> None:
    client = RecordingClient()
    data = _image_bytes(format_name)
    filename = "plan.png" if content_type == "image/png" else "plan.jpg"
    request = _request(
        PlanReferenceBlob(
            filename=filename,
            content_type=content_type,
            kind=PlanReferenceKind.IMAGE,
            data=data,
        )
    )

    result = PlanIntakeService(_provider(client)).recognize(request)

    call = client.calls[0]
    assert call["models"] == (VISION_MODEL,)
    assert call["max_tokens"] == 4096
    assert call["disable_thinking"] is True
    assert "response_format" not in call
    user_content = call["messages"][1]["content"]
    image_part = next(part for part in user_content if part["type"] == "image_url")
    image_url = image_part["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")
    provider_bytes = base64.b64decode(image_url.partition(",")[2])
    if content_type == "image/png":
        assert provider_bytes == data
    else:
        assert provider_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        assert not provider_bytes.startswith(b"\xff\xd8\xff")
    assert result.reference_names == (filename,)
    assert result.provider == "nvidia_nim"
    assert result.model == VISION_MODEL
    assert result.content_hash == result.compute_content_hash()
    assert result.envelope.source is PlanObservationSource.IMAGE
    assert result.envelope.requires_confirmation is True
    assert result.orientation.requires_confirmation is True
    assert result.rooms[0].requires_confirmation is True


def test_nvidia_pdf_path_sends_only_locally_rendered_png_without_raster_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ai_vastu.plan_intake.nvidia_nim_provider.normalize_nvidia_plan_raster",
        lambda *_args: pytest.fail("PDF pages entered upload raster normalization"),
    )
    client = RecordingClient()
    request = _request(
        PlanReferenceBlob(
            filename="floor-plan.pdf",
            content_type="application/pdf",
            kind=PlanReferenceKind.PDF,
            data=b"raw-pdf-must-stay-local",
        )
    )

    result = PlanIntakeService(
        _provider(client, pdf_renderer=StubPdfRenderer())
    ).recognize(request)

    serialized_messages = repr(client.calls[0]["messages"])
    assert client.calls[0]["disable_thinking"] is True
    assert "response_format" not in client.calls[0]
    assert "raw-pdf-must-stay-local" not in serialized_messages
    assert "data:application/pdf" not in serialized_messages
    assert (
        "data:image/png;base64,"
        + base64.b64encode(b"rendered-page-png").decode("ascii")
    ) in serialized_messages
    assert result.envelope.source is PlanObservationSource.PDF
    assert result.content_hash == result.compute_content_hash()
    assert any("rendered locally" in warning for warning in result.warnings)


def test_nvidia_pdf_failure_is_sanitized() -> None:
    request = _request(
        PlanReferenceBlob(
            filename="floor-plan.pdf",
            content_type="application/pdf",
            kind=PlanReferenceKind.PDF,
            data=b"bad-pdf",
        )
    )

    with pytest.raises(PlanIntakeProviderError) as captured:
        _provider(RecordingClient(), pdf_renderer=FailingPdfRenderer()).recognize(request)

    assert str(captured.value) == "Plan recognition provider failed."
    assert "sensitive parser detail" not in str(captured.value)


def test_nvidia_malformed_jpeg_failure_is_sanitized_before_provider_call() -> None:
    client = RecordingClient()
    request = _request(
        PlanReferenceBlob(
            filename="private-plan.jpg",
            content_type="image/jpeg",
            kind=PlanReferenceKind.IMAGE,
            data=b"\xff\xd8\xffprivate-image-payload",
        )
    )

    with pytest.raises(PlanIntakeProviderError) as captured:
        _provider(client).recognize(request)

    assert client.calls == []
    assert str(captured.value) == "Plan recognition provider failed."
    assert "private-plan" not in str(captured.value)
    assert "private-image-payload" not in str(captured.value)


def test_plan_recognition_draft_rejects_tampered_content_hash() -> None:
    client = RecordingClient()
    result = PlanIntakeService(_provider(client)).recognize(
        _request(
            PlanReferenceBlob(
                filename="plan.png",
                content_type="image/png",
                kind=PlanReferenceKind.IMAGE,
                data=_image_bytes("PNG"),
            )
        )
    )
    tampered = result.model_dump()
    tampered["content_hash"] = "0" * 64

    with pytest.raises(ValueError, match="content_hash does not match"):
        PlanRecognitionDraft.model_validate(tampered)


def test_nvidia_plan_provider_factory_requires_no_legacy_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "nvidia_nim")
    monkeypatch.setenv("NVIDIA_API_KEY", "not-a-live-secret")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    provider = create_plan_recognition_provider()

    assert isinstance(provider, NvidiaNimPlanRecognitionProvider)
