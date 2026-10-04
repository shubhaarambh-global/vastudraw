from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest
from PIL import Image

from ai_vastu.apinex_http import APINEX_API_BASE, APINEX_MODEL, ApinexConfigurationError
from ai_vastu.architectural_brain.apinex_provider import ApinexArchitecturalBrainProvider
from ai_vastu.architectural_brain.apinex_revision import interpret_revision_with_apinex
from ai_vastu.architectural_brain.models import (
    ArchitecturalConcept,
    StructuredRevisionIntent,
)
from ai_vastu.architectural_brain.provider import create_architectural_brain_provider
from ai_vastu.architectural_brain.revisions import interpret_revision
from ai_vastu.architectural_intelligence.models import ArchitecturalDesignIntent
from ai_vastu.architectural_intelligence.providers.apinex import (
    ApinexArchitecturalIntelligenceProvider,
)
from ai_vastu.architectural_intelligence.providers.base import ArchitecturalReasoningInput
from ai_vastu.architectural_intelligence.service import (
    create_architectural_intelligence_provider,
)
from ai_vastu.pdf_render_adapter import RenderedPdfPage
from ai_vastu.plan_intake import (
    ApinexPlanRecognitionProvider,
    PlanIntakeConfigurationError,
    PlanIntakeProviderError,
    PlanIntakeService,
    PlanObservationSource,
    PlanRecognitionDraft,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
)
from ai_vastu.plan_intake.service import create_plan_recognition_provider
from ai_vastu.requirements.errors import RequirementsConfigurationError
from ai_vastu.requirements.models import (
    ConfirmedRequirements,
    ConfirmedRoomRequirement,
    Direction,
    EvidenceSource,
    RequirementDraft,
    VastuMode,
)
from ai_vastu.requirements.providers.apinex import ApinexRequirementsProvider
from ai_vastu.requirements.providers.base import InterpretationInput, ReferenceAsset
from ai_vastu.requirements.providers.fixture import FixtureRequirementsProvider
from ai_vastu.requirements.service import create_provider
from ai_vastu.vastu_reasoning.catalog import load_soft_vastu_catalog
from ai_vastu.vastu_reasoning.models import VastuReasoningProfile
from ai_vastu.vastu_reasoning.providers.apinex import ApinexVastuReasoningProvider
from ai_vastu.vastu_reasoning.providers.base import VastuReasoningInput
from ai_vastu.vastu_reasoning.service import create_vastu_reasoning_provider

PROJECT_ID = UUID("30000000-0000-0000-0000-000000000029")
DRAFT_ID = UUID("10000000-0000-0000-0000-000000000029")
USER_ID = UUID("20000000-0000-0000-0000-000000000029")
INTAKE_ID = UUID("40000000-0000-0000-0000-000000000029")
REVISION_ID = UUID("50000000-0000-0000-0000-000000000029")


class RecordingClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def complete_validated_json(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return kwargs["validator"](self.payload, APINEX_MODEL)


def _confirmed() -> ConfirmedRequirements:
    return ConfirmedRequirements(
        draft_id=DRAFT_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        user_confirmed=True,
        plot_width_mm=9000,
        plot_depth_mm=15000,
        north_rotation_deg=0,
        road_side=Direction.N,
        entrance_facing=None,
        floor_count=1,
        bedroom_count=2,
        parking_count=1,
        vastu_mode=VastuMode.BALANCED,
        rooms=[
            ConfirmedRoomRequirement(room_type="bedroom", quantity=2),
            ConfirmedRoomRequirement(room_type="living"),
            ConfirmedRoomRequirement(room_type="kitchen"),
            ConfirmedRoomRequirement(room_type="common_toilet"),
        ],
    )


def _image(format_name: str) -> bytes:
    output = io.BytesIO()
    with Image.new("RGB", (64, 48), "white") as image:
        image.save(output, format=format_name)
    return output.getvalue()


def _plan_payload() -> dict[str, Any]:
    return {
        "envelope": {
            "geometry_type": "UNKNOWN",
            "confidence": 0.8,
            "source": "USER_CONFIRMED",
            "requires_confirmation": False,
            "evidence": ["visible boundary"],
        },
        "orientation": {
            "north_rotation_deg": 0,
            "confidence": 0.9,
            "source": "USER_CONFIRMED",
            "requires_confirmation": False,
            "evidence": ["north arrow"],
        },
        "rooms": [
            {
                "room_type": "living",
                "label": "LIVING",
                "confidence": 0.9,
                "source": "USER_CONFIRMED",
                "requires_confirmation": False,
                "evidence": ["label"],
            }
        ],
        "observations": ["NORTH and LIVING are visible."],
        "questions": [],
        "warnings": [],
    }


def test_requirements_real_contract_and_application_authority() -> None:
    request = InterpretationInput(
        draft_id=DRAFT_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        prompt="9000 x 15000 mm, north road, two bedrooms.",
        references=(ReferenceAsset("brief.txt", "text/plain", b"synthetic"),),
    )
    payload = (
        FixtureRequirementsProvider()
        .interpret(request)
        .model_dump(
            mode="json",
            exclude={
                "draft_id",
                "user_id",
                "project_id",
                "prompt",
                "reference_names",
                "provider",
                "model",
            },
        )
    )
    payload["plot_width_mm"]["source"] = "user_confirmed"
    payload["plot_width_mm"]["requires_confirmation"] = False
    payload["rooms"] = [
        {
            "room_type": "bedroom",
            "quantity": 2,
            "source": "user_confirmed",
            "confidence": 0.9,
        }
    ]
    client = RecordingClient(payload)

    draft = ApinexRequirementsProvider(client=cast(Any, client)).interpret(request)

    assert client.calls[0]["schema"] == RequirementDraft.model_json_schema()
    assert (draft.draft_id, draft.user_id, draft.project_id) == (
        DRAFT_ID,
        USER_ID,
        PROJECT_ID,
    )
    assert draft.prompt == request.prompt
    assert draft.reference_names == ["brief.txt"]
    assert draft.provider == "apinex"
    assert draft.model == APINEX_MODEL
    assert draft.plot_width_mm is not None
    assert draft.plot_width_mm.requires_confirmation is True
    assert draft.plot_width_mm.source is EvidenceSource.MODEL_INFERENCE
    assert all(room.source is not EvidenceSource.USER_CONFIRMED for room in draft.rooms)


def test_architectural_intelligence_remains_advisory_and_hashed() -> None:
    request = ArchitecturalReasoningInput(
        confirmed=_confirmed(),
        original_prompt="Synthetic functional home.",
        precedent_context=(),
    )
    from ai_vastu.architectural_intelligence.providers.fixture import (
        FixtureArchitecturalIntelligenceProvider,
    )

    payload = FixtureArchitecturalIntelligenceProvider().reason(request).model_dump(
        mode="json",
        exclude={"project_id", "draft_id", "provider", "model", "content_hash"},
    )
    client = RecordingClient(payload)
    intent = ApinexArchitecturalIntelligenceProvider(
        client=cast(Any, client)
    ).reason(request)
    assert client.calls[0]["schema"] == ArchitecturalDesignIntent.model_json_schema()
    assert intent.provider == "apinex"
    assert intent.model == APINEX_MODEL
    assert intent.content_hash == intent.compute_content_hash()


def test_vastu_reasoning_uses_soft_catalog_contract() -> None:
    request = VastuReasoningInput(
        confirmed=_confirmed(),
        original_prompt="Synthetic balanced soft Vastu.",
        catalog=load_soft_vastu_catalog(),
    )
    from ai_vastu.vastu_reasoning.providers.fixture import FixtureVastuReasoningProvider

    payload = FixtureVastuReasoningProvider().reason(request).model_dump(
        mode="json",
        exclude={"project_id", "draft_id", "provider", "model", "content_hash"},
    )
    client = RecordingClient(payload)
    profile = ApinexVastuReasoningProvider(client=cast(Any, client)).reason(request)
    assert client.calls[0]["schema"] == VastuReasoningProfile.model_json_schema()
    assert profile.provider == "apinex"
    assert profile.model == APINEX_MODEL
    assert profile.content_hash == profile.compute_content_hash()
    assert all(rule.hard_constraint is False for rule in request.catalog.rules)


def test_architectural_brain_output_remains_non_authoritative() -> None:
    client = RecordingClient(
        {
            "concepts": [
                {
                    "project_id": str(UUID(int=0)),
                    "concept_id": "apinex-concept-1",
                    "title": "Synthetic advisory topology",
                    "rooms": [],
                    "topology": [],
                    "precedent_ids": [],
                    "design_rationale": ["Advisory only."],
                    "authoritative_geometry": True,
                }
            ]
        }
    )
    concepts = ApinexArchitecturalBrainProvider(client=cast(Any, client)).propose(
        project_id=PROJECT_ID,
        original_prompt="Synthetic compact home.",
        width_mm=9000,
        depth_mm=15000,
        bedroom_count=2,
        toilet_count=1,
        parking_count=1,
        room_types=("living", "kitchen", "bedroom", "common_toilet"),
        road_side="N",
        entrance_side=None,
        precedents=(),
        concept_count=1,
    )
    assert client.calls[0]["schema"]["properties"]["concepts"]["type"] == "array"
    assert isinstance(concepts[0], ArchitecturalConcept)
    assert concepts[0].project_id == PROJECT_ID
    assert concepts[0].authoritative_geometry is False
    assert concepts[0].content_hash == concepts[0].compute_content_hash()


def test_revision_identity_and_authority_are_application_owned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = RecordingClient(
        {
            "project_id": str(UUID(int=0)),
            "base_revision_id": str(UUID(int=0)),
            "original_request": "unsafe replacement",
            "directives": [],
            "preserve_unmentioned_requirements": False,
            "authoritative_geometry": True,
        }
    )
    monkeypatch.setattr(
        "ai_vastu.architectural_brain.apinex_revision.ApinexClient.from_environment",
        lambda: cast(Any, client),
    )
    intent = interpret_revision_with_apinex(
        project_id=PROJECT_ID,
        base_revision_id=REVISION_ID,
        request="Make the living room wider.",
    )
    assert client.calls[0]["schema"] == StructuredRevisionIntent.model_json_schema()
    assert intent.project_id == PROJECT_ID
    assert intent.base_revision_id == REVISION_ID
    assert intent.original_request == "Make the living room wider."
    assert intent.preserve_unmentioned_requirements is True
    assert intent.authoritative_geometry is False


@pytest.mark.parametrize(
    ("content_type", "format_name", "signature"),
    (
        ("image/png", "PNG", b"\x89PNG\r\n\x1a\n"),
        ("image/jpeg", "JPEG", b"\xff\xd8\xff"),
    ),
)
def test_plan_raster_real_contract_provenance_and_hash(
    content_type: str, format_name: str, signature: bytes
) -> None:
    client = RecordingClient(_plan_payload())
    draft = PlanIntakeService(ApinexPlanRecognitionProvider(client=cast(Any, client))).recognize(
        PlanRecognitionInput(
            project_id=PROJECT_ID,
            intake_id=INTAKE_ID,
            prompt="Recognize visible synthetic evidence.",
            references=(
                PlanReferenceBlob(
                    filename=f"plan.{format_name.lower()}",
                    content_type=content_type,
                    kind=PlanReferenceKind.IMAGE,
                    data=_image(format_name),
                ),
            ),
        )
    )

    sent = base64.b64decode(client.calls[0]["messages"][1]["images"][0])
    assert sent.startswith(signature)
    assert client.calls[0]["schema"] == PlanRecognitionDraft.model_json_schema()
    assert draft.schema_version == "26B.5.1"
    assert draft.provider == "apinex"
    assert draft.model == APINEX_MODEL
    assert draft.reference_names == (f"plan.{format_name.lower()}",)
    assert draft.content_hash == draft.compute_content_hash()
    assert draft.envelope.requires_confirmation is True
    assert draft.orientation.requires_confirmation is True
    assert draft.rooms[0].requires_confirmation is True
    assert draft.envelope.source is PlanObservationSource.MODEL_INFERENCE
    assert draft.orientation.source is PlanObservationSource.MODEL_INFERENCE
    assert draft.rooms[0].source is PlanObservationSource.MODEL_INFERENCE


def test_pdf_is_locally_rendered_and_only_png_reaches_apinex() -> None:
    raw_pdf = b"%PDF-synthetic-raw"
    rendered_png = _image("PNG")

    class Renderer:
        def render(self, *, filename: str, data: bytes) -> tuple[RenderedPdfPage, ...]:
            assert filename == "plan.pdf"
            assert data == raw_pdf
            return (RenderedPdfPage(1, "plan.pdf#page-1.png", "image/png", rendered_png),)

    client = RecordingClient(_plan_payload())
    draft = PlanIntakeService(
        ApinexPlanRecognitionProvider(client=cast(Any, client), pdf_renderer=Renderer())
    ).recognize(
        PlanRecognitionInput(
            project_id=PROJECT_ID,
            intake_id=INTAKE_ID,
            prompt="Synthetic PDF qualification.",
            references=(
                PlanReferenceBlob(
                    filename="plan.pdf",
                    content_type="application/pdf",
                    kind=PlanReferenceKind.PDF,
                    data=raw_pdf,
                ),
            ),
        )
    )
    sent = base64.b64decode(client.calls[0]["messages"][1]["images"][0])
    assert sent == rendered_png
    assert raw_pdf not in sent
    assert draft.reference_names == ("plan.pdf",)
    assert draft.content_hash == draft.compute_content_hash()


@pytest.mark.parametrize(
    ("content_type", "data"),
    (
        ("image/png", b"not-png"),
        ("image/jpeg", b"\x89PNG\r\n\x1a\nwrong-mime"),
        ("image/gif", b"GIF89a"),
    ),
)
def test_malformed_or_mismatched_images_fail_before_provider(
    content_type: str, data: bytes
) -> None:
    client = RecordingClient(_plan_payload())
    provider = ApinexPlanRecognitionProvider(client=cast(Any, client))
    with pytest.raises(PlanIntakeProviderError):
        provider.recognize(
            PlanRecognitionInput(
                project_id=PROJECT_ID,
                intake_id=INTAKE_ID,
                prompt="Synthetic.",
                references=(
                    PlanReferenceBlob(
                        filename="untrusted",
                        content_type=content_type,
                        kind=PlanReferenceKind.IMAGE,
                        data=data,
                    ),
                ),
            )
        )
    assert client.calls == []


def _select_all(monkeypatch: pytest.MonkeyPatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("APINEX_API_KEY", "synthetic")
    monkeypatch.setenv("AI_VASTU_APINEX_BASE_URL", APINEX_API_BASE)
    monkeypatch.setenv("AI_VASTU_APINEX_MODEL", APINEX_MODEL)
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PROVIDER", "apinex")
    monkeypatch.setenv("AI_VASTU_ARCHITECT_PROVIDER", "apinex")
    monkeypatch.setenv("AI_VASTU_VASTU_PROVIDER", "apinex")
    monkeypatch.setenv("AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER", "apinex")
    monkeypatch.setenv("AI_VASTU_REVISION_PROVIDER", "apinex")
    monkeypatch.setenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "apinex")


def test_development_factories_select_apinex_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _select_all(monkeypatch, "development")
    assert isinstance(create_provider(), ApinexRequirementsProvider)
    assert isinstance(
        create_architectural_intelligence_provider(),
        ApinexArchitecturalIntelligenceProvider,
    )
    assert isinstance(create_vastu_reasoning_provider(), ApinexVastuReasoningProvider)
    assert isinstance(create_architectural_brain_provider(), ApinexArchitecturalBrainProvider)
    assert isinstance(create_plan_recognition_provider(), ApinexPlanRecognitionProvider)


@pytest.mark.parametrize("app_env", ("staging", "production"))
def test_staging_and_production_reject_apinex_before_http(
    monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    _select_all(monkeypatch, app_env)
    with pytest.raises((RequirementsConfigurationError, RuntimeError)):
        create_provider()
    with pytest.raises(RuntimeError):
        create_architectural_intelligence_provider()
    with pytest.raises(RuntimeError):
        create_vastu_reasoning_provider()
    with pytest.raises(RuntimeError):
        create_architectural_brain_provider()
    with pytest.raises(PlanIntakeConfigurationError):
        create_plan_recognition_provider()
    with pytest.raises((ApinexConfigurationError, RuntimeError)):
        interpret_revision(
            project_id=PROJECT_ID,
            base_revision_id=DRAFT_ID,
            request="No network call.",
        )


def test_apinex_is_not_the_default_and_profile_contains_no_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "AI_VASTU_REQUIREMENTS_PROVIDER",
        "AI_VASTU_ARCHITECT_PROVIDER",
        "AI_VASTU_VASTU_PROVIDER",
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
        "AI_VASTU_REVISION_PROVIDER",
        "AI_VASTU_PLAN_RECOGNITION_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    assert create_provider().name != "apinex"
    root = Path(__file__).resolve().parents[2]
    profile = (root / "phase29-apinex.env.example").read_text(encoding="utf-8")
    assert profile.count("=apinex") == 6
    assert "APINEX_API_KEY" not in profile
    assert "free/gpt-6-luna" in profile
