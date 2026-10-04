from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import pytest

from ai_vastu.architectural_brain.errors import ArchitecturalBrainConfigurationError
from ai_vastu.architectural_brain.models import StructuredRevisionIntent
from ai_vastu.architectural_brain.ollama_local_provider import (
    OllamaLocalArchitecturalBrainProvider,
)
from ai_vastu.architectural_brain.ollama_local_revision import (
    interpret_revision_with_ollama_local,
)
from ai_vastu.architectural_brain.provider import create_architectural_brain_provider
from ai_vastu.architectural_intelligence.errors import (
    ArchitecturalIntelligenceConfigurationError,
)
from ai_vastu.architectural_intelligence.models import ArchitecturalDesignIntent
from ai_vastu.architectural_intelligence.providers.base import ArchitecturalReasoningInput
from ai_vastu.architectural_intelligence.providers.fixture import (
    FixtureArchitecturalIntelligenceProvider,
)
from ai_vastu.architectural_intelligence.providers.ollama_local import (
    OllamaLocalArchitecturalIntelligenceProvider,
)
from ai_vastu.architectural_intelligence.service import (
    create_architectural_intelligence_provider,
)
from ai_vastu.ollama_local_http import (
    OLLAMA_LOCAL_BASE_URL,
    OLLAMA_LOCAL_MODEL,
    OllamaLocalClient,
    OllamaLocalConfigurationError,
)
from ai_vastu.plan_intake.errors import PlanIntakeConfigurationError
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
from ai_vastu.requirements.providers.base import InterpretationInput, ReferenceAsset
from ai_vastu.requirements.providers.fixture import FixtureRequirementsProvider
from ai_vastu.requirements.providers.ollama_local import OllamaLocalRequirementsProvider
from ai_vastu.requirements.service import create_provider
from ai_vastu.vastu_reasoning.catalog import load_soft_vastu_catalog
from ai_vastu.vastu_reasoning.errors import VastuReasoningConfigurationError
from ai_vastu.vastu_reasoning.models import VastuReasoningProfile
from ai_vastu.vastu_reasoning.providers.base import VastuReasoningInput
from ai_vastu.vastu_reasoning.providers.fixture import FixtureVastuReasoningProvider
from ai_vastu.vastu_reasoning.providers.ollama_local import (
    OllamaLocalVastuReasoningProvider,
)
from ai_vastu.vastu_reasoning.service import create_vastu_reasoning_provider

PROJECT_ID = UUID("30000000-0000-0000-0000-000000000029")
DRAFT_ID = UUID("10000000-0000-0000-0000-000000000029")
USER_ID = UUID("20000000-0000-0000-0000-000000000029")
REVISION_ID = UUID("40000000-0000-0000-0000-000000000029")


class RecordingClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def complete_validated_json(self, **kwargs: Any) -> object:
        self.calls.append(kwargs)
        return kwargs["validator"](self.payload, OLLAMA_LOCAL_MODEL)


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


def test_requirements_adapter_uses_real_schema_and_restores_authority() -> None:
    request = InterpretationInput(
        draft_id=DRAFT_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        prompt="9000 x 15000 mm, north road, 2 bedrooms, one-car parking.",
        references=(ReferenceAsset("brief.txt", "text/plain", b"sentinel"),),
    )
    payload = FixtureRequirementsProvider().interpret(request).model_dump(
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
    payload["plot_width_mm"]["source"] = "user_confirmed"
    payload["plot_width_mm"]["requires_confirmation"] = False
    payload["rooms"][0]["source"] = "user_confirmed"
    client = RecordingClient(payload)

    draft = OllamaLocalRequirementsProvider(client=cast(Any, client)).interpret(request)

    assert client.calls[0]["schema"] == RequirementDraft.model_json_schema()
    assert draft.draft_id == request.draft_id
    assert draft.user_id == request.user_id
    assert draft.project_id == request.project_id
    assert draft.prompt == request.prompt
    assert draft.reference_names == ["brief.txt"]
    assert draft.provider == "ollama_local"
    assert draft.model == OLLAMA_LOCAL_MODEL
    assert draft.plot_width_mm is not None
    assert draft.plot_width_mm.requires_confirmation is True
    assert draft.plot_width_mm.source is EvidenceSource.MODEL_INFERENCE
    assert draft.rooms[0].source is EvidenceSource.MODEL_INFERENCE


def test_requirements_adapter_preserves_prompt_room_evidence() -> None:
    request = InterpretationInput(
        draft_id=DRAFT_ID,
        user_id=USER_ID,
        project_id=PROJECT_ID,
        prompt="Two bedrooms are explicitly requested.",
        references=(),
    )
    payload = FixtureRequirementsProvider().interpret(request).model_dump(
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
    payload["rooms"] = [
        {
            "room_type": "bedroom",
            "quantity": 2,
            "source": EvidenceSource.PROMPT.value,
            "confidence": 0.9,
        }
    ]

    draft = OllamaLocalRequirementsProvider(
        client=cast(Any, RecordingClient(payload))
    ).interpret(request)

    assert draft.rooms[0].source is EvidenceSource.PROMPT


def test_architectural_adapter_uses_real_advisory_contract_schema() -> None:
    request = ArchitecturalReasoningInput(
        confirmed=_confirmed(),
        original_prompt="Functional two-bedroom home.",
        precedent_context=(),
    )
    payload = FixtureArchitecturalIntelligenceProvider().reason(request).model_dump(
        mode="json",
        exclude={"project_id", "draft_id", "provider", "model", "content_hash"},
    )
    client = RecordingClient(payload)

    intent = OllamaLocalArchitecturalIntelligenceProvider(
        client=cast(Any, client)
    ).reason(request)

    assert client.calls[0]["schema"] == ArchitecturalDesignIntent.model_json_schema()
    assert intent.project_id == PROJECT_ID
    assert intent.draft_id == DRAFT_ID
    assert intent.provider == "ollama_local"
    assert intent.model == OLLAMA_LOCAL_MODEL
    assert intent.content_hash == intent.compute_content_hash()


def test_vastu_adapter_uses_real_soft_contract_schema() -> None:
    request = VastuReasoningInput(
        confirmed=_confirmed(),
        original_prompt="Balanced soft Vastu.",
        catalog=load_soft_vastu_catalog(),
    )
    payload = FixtureVastuReasoningProvider().reason(request).model_dump(
        mode="json",
        exclude={"project_id", "draft_id", "provider", "model", "content_hash"},
    )
    client = RecordingClient(payload)

    profile = OllamaLocalVastuReasoningProvider(client=cast(Any, client)).reason(request)

    assert client.calls[0]["schema"] == VastuReasoningProfile.model_json_schema()
    assert profile.provider == "ollama_local"
    assert profile.model == OLLAMA_LOCAL_MODEL
    assert profile.content_hash == profile.compute_content_hash()
    assert all(rule.hard_constraint is False for rule in request.catalog.rules)


def test_architectural_brain_uses_concepts_batch_schema_and_advisory_output() -> None:
    client = RecordingClient(
        {
            "concepts": [
                {
                    "project_id": str(UUID(int=0)),
                    "concept_id": "local-concept-1",
                    "title": "Compact advisory topology",
                    "rooms": [],
                    "topology": [],
                    "precedent_ids": [],
                    "design_rationale": ["Advisory only."],
                    "authoritative_geometry": False,
                }
            ]
        }
    )
    provider = OllamaLocalArchitecturalBrainProvider(client=cast(Any, client))

    concepts = provider.propose(
        project_id=PROJECT_ID,
        original_prompt="Compact home.",
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

    schema = client.calls[0]["schema"]
    assert schema["properties"]["concepts"]["type"] == "array"
    assert concepts[0].project_id == PROJECT_ID
    assert concepts[0].authoritative_geometry is False
    assert concepts[0].content_hash == concepts[0].compute_content_hash()


def test_revision_adapter_overwrites_identity_and_advisory_flags(
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
        OllamaLocalClient,
        "from_environment",
        classmethod(lambda _cls: cast(Any, client)),
    )

    intent = interpret_revision_with_ollama_local(
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


def _select_all_ollama(monkeypatch: pytest.MonkeyPatch, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("AI_VASTU_OLLAMA_BASE_URL", OLLAMA_LOCAL_BASE_URL)
    monkeypatch.setenv("AI_VASTU_OLLAMA_MODEL", OLLAMA_LOCAL_MODEL)
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PROVIDER", "ollama_local")
    monkeypatch.setenv("AI_VASTU_ARCHITECT_PROVIDER", "ollama_local")
    monkeypatch.setenv("AI_VASTU_VASTU_PROVIDER", "ollama_local")
    monkeypatch.setenv("AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER", "ollama_local")
    monkeypatch.setenv("AI_VASTU_REVISION_PROVIDER", "ollama_local")
    monkeypatch.setenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "ollama_local")


def test_development_factories_select_first_class_ollama_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _select_all_ollama(monkeypatch, "development")

    assert create_provider().name == "ollama_local"
    assert create_architectural_intelligence_provider().name == "ollama_local"
    assert create_vastu_reasoning_provider().name == "ollama_local"
    assert isinstance(
        create_architectural_brain_provider(),
        OllamaLocalArchitecturalBrainProvider,
    )
    assert create_plan_recognition_provider().name == "ollama_local"


@pytest.mark.parametrize("app_env", ("staging", "production"))
def test_staging_and_production_reject_every_ollama_selector_before_http(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
) -> None:
    _select_all_ollama(monkeypatch, app_env)

    with pytest.raises(RequirementsConfigurationError):
        create_provider()
    with pytest.raises(ArchitecturalIntelligenceConfigurationError):
        create_architectural_intelligence_provider()
    with pytest.raises(VastuReasoningConfigurationError):
        create_vastu_reasoning_provider()
    with pytest.raises(ArchitecturalBrainConfigurationError):
        create_architectural_brain_provider()
    with pytest.raises(PlanIntakeConfigurationError):
        create_plan_recognition_provider()
    with pytest.raises(OllamaLocalConfigurationError):
        interpret_revision_with_ollama_local(
            project_id=PROJECT_ID,
            base_revision_id=REVISION_ID,
            request="No network call may occur.",
        )


def test_dedicated_profile_has_all_six_selectors_and_no_credentials() -> None:
    root = Path(__file__).resolve().parents[2]
    values = (root / "phase29-ollama-local.env.example").read_text(encoding="utf-8")
    assert "APP_ENV=development" in values
    assert values.count("=ollama_local") == 6
    assert f"AI_VASTU_OLLAMA_BASE_URL={OLLAMA_LOCAL_BASE_URL}" in values
    assert f"AI_VASTU_OLLAMA_MODEL={OLLAMA_LOCAL_MODEL}" in values
    assert "AI_VASTU_OLLAMA_READ_TIMEOUT_SECONDS=300" in values
    assert "AI_VASTU_OLLAMA_TOTAL_TIMEOUT_SECONDS=360" in values
    assert "API_KEY" not in values
    assert "AI_VASTU_PAYMENT_" not in values
    assert json.loads((root / "package.json").read_text(encoding="utf-8"))["scripts"][
        "ollama:local"
    ] == "node scripts/run-project-python.mjs scripts/check-ollama-local.py"
