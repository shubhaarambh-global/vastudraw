from __future__ import annotations

import base64
import io
from typing import Any, cast
from uuid import UUID

import pytest
from PIL import Image

from ai_vastu.ollama_local_http import OLLAMA_LOCAL_MODEL
from ai_vastu.pdf_render_adapter import RenderedPdfPage
from ai_vastu.plan_intake import (
    PlanIntakeProviderError,
    PlanIntakeService,
    PlanObservationSource,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
)
from ai_vastu.plan_intake.ollama_local_provider import (
    OllamaLocalPlanRecognitionProvider,
)

PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
INTAKE_ID = UUID("22222222-2222-2222-2222-222222222222")


class RecordingClient:
    def __init__(self, *, source: str = "USER_CONFIRMED") -> None:
        self.calls: list[dict[str, Any]] = []
        self.source = source

    def complete_validated_json(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        payload = {
            "envelope": {
                "geometry_type": "UNKNOWN",
                "confidence": 0.8,
                "source": self.source,
                "requires_confirmation": False,
                "evidence": ["visible boundary"],
            },
            "orientation": {
                "north_rotation_deg": 0,
                "confidence": 0.9,
                "source": self.source,
                "requires_confirmation": False,
                "evidence": ["north arrow"],
            },
            "rooms": [
                {
                    "room_type": "living",
                    "label": "LIVING",
                    "confidence": 0.9,
                    "source": self.source,
                    "requires_confirmation": False,
                    "evidence": ["label"],
                }
            ],
            "observations": ["NORTH and LIVING are visible."],
            "questions": [],
            "warnings": [],
        }
        return kwargs["validator"](payload, OLLAMA_LOCAL_MODEL)


def _image(format_name: str) -> bytes:
    output = io.BytesIO()
    with Image.new("RGB", (64, 48), "white") as image:
        image.save(output, format=format_name)
    return output.getvalue()


def _request(reference: PlanReferenceBlob) -> PlanRecognitionInput:
    return PlanRecognitionInput(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        prompt="Recognize only visible plan evidence.",
        references=(reference,),
    )


@pytest.mark.parametrize(
    ("content_type", "format_name", "signature"),
    (
        ("image/png", "PNG", b"\x89PNG\r\n\x1a\n"),
        ("image/jpeg", "JPEG", b"\xff\xd8\xff"),
    ),
)
def test_ollama_plan_provider_sends_validated_raster_bytes_unchanged(
    content_type: str,
    format_name: str,
    signature: bytes,
) -> None:
    client = RecordingClient()
    data = _image(format_name)
    service = PlanIntakeService(
        OllamaLocalPlanRecognitionProvider(client=cast(Any, client))
    )

    draft = service.recognize(
        _request(
            PlanReferenceBlob(
                filename=f"plan.{format_name.lower()}",
                content_type=content_type,
                kind=PlanReferenceKind.IMAGE,
                data=data,
            )
        )
    )

    body_message = client.calls[0]["messages"][1]
    sent = base64.b64decode(body_message["images"][0])
    assert sent == data
    assert sent.startswith(signature)
    assert client.calls[0]["schema"] == draft.model_json_schema()
    assert draft.provider == "ollama_local"
    assert draft.model == OLLAMA_LOCAL_MODEL
    assert draft.schema_version == "26B.5.1"
    assert draft.reference_names == (f"plan.{format_name.lower()}",)
    assert draft.content_hash == draft.compute_content_hash()
    assert draft.envelope.requires_confirmation is True
    assert draft.orientation.requires_confirmation is True
    assert draft.rooms[0].requires_confirmation is True
    assert draft.envelope.source is PlanObservationSource.MODEL_INFERENCE
    assert draft.orientation.source is PlanObservationSource.MODEL_INFERENCE
    assert draft.rooms[0].source is PlanObservationSource.MODEL_INFERENCE


def test_ollama_pdf_uses_existing_renderer_and_sends_png_only() -> None:
    raw_pdf = b"%PDF-raw-sentinel"
    rendered_png = b"\x89PNG\r\n\x1a\nrendered-sentinel"

    class RecordingRenderer:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bytes]] = []

        def render(self, *, filename: str, data: bytes) -> tuple[RenderedPdfPage, ...]:
            self.calls.append((filename, data))
            return (
                RenderedPdfPage(
                    page_number=1,
                    filename=f"{filename}#page-1.png",
                    content_type="image/png",
                    data=rendered_png,
                ),
            )

    client = RecordingClient()
    renderer = RecordingRenderer()
    service = PlanIntakeService(
        OllamaLocalPlanRecognitionProvider(
            client=cast(Any, client),
            pdf_renderer=renderer,
        )
    )

    draft = service.recognize(
        _request(
            PlanReferenceBlob(
                filename="plan.pdf",
                content_type="application/pdf",
                kind=PlanReferenceKind.PDF,
                data=raw_pdf,
            )
        )
    )

    assert renderer.calls == [("plan.pdf", raw_pdf)]
    sent = base64.b64decode(client.calls[0]["messages"][1]["images"][0])
    assert sent == rendered_png
    assert raw_pdf not in sent
    assert draft.content_hash == draft.compute_content_hash()
    assert any("rendered locally" in warning for warning in draft.warnings)


@pytest.mark.parametrize("hostile_source", ("CAD_EXTRACTION", "DWG", "PDF", "IMAGE"))
def test_ollama_visual_observations_are_always_model_inferences(
    hostile_source: str,
) -> None:
    client = RecordingClient(source=hostile_source)
    draft = PlanIntakeService(
        OllamaLocalPlanRecognitionProvider(client=cast(Any, client))
    ).recognize(
        _request(
            PlanReferenceBlob(
                filename="plan.png",
                content_type="image/png",
                kind=PlanReferenceKind.IMAGE,
                data=_image("PNG"),
            )
        )
    )

    assert draft.envelope.source is PlanObservationSource.MODEL_INFERENCE
    assert draft.orientation.source is PlanObservationSource.MODEL_INFERENCE
    assert draft.rooms[0].source is PlanObservationSource.MODEL_INFERENCE
    assert draft.envelope.requires_confirmation is True
    assert draft.orientation.requires_confirmation is True
    assert draft.rooms[0].requires_confirmation is True


@pytest.mark.parametrize(
    ("content_type", "data"),
    (
        ("image/png", b"not-png"),
        ("image/jpeg", b"\x89PNG\r\n\x1a\nwrong-mime"),
        ("image/gif", b"GIF89a"),
    ),
)
def test_ollama_plan_provider_rejects_malformed_images_before_http(
    content_type: str,
    data: bytes,
) -> None:
    client = RecordingClient()
    provider = OllamaLocalPlanRecognitionProvider(client=cast(Any, client))

    with pytest.raises(PlanIntakeProviderError) as captured:
        provider.recognize(
            _request(
                PlanReferenceBlob(
                    filename="untrusted-image",
                    content_type=content_type,
                    kind=PlanReferenceKind.IMAGE,
                    data=data,
                )
            )
        )

    assert str(captured.value) == "Plan recognition provider failed."
    assert client.calls == []
    assert "untrusted-image" not in str(captured.value)
