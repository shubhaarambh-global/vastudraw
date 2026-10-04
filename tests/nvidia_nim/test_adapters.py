from __future__ import annotations

import json
from uuid import UUID

import httpx

from ai_vastu.architectural_brain.nvidia_nim_provider import (
    NvidiaNimArchitecturalBrainProvider,
)
from ai_vastu.architectural_brain.provider import create_architectural_brain_provider
from ai_vastu.architectural_brain.revisions import interpret_revision
from ai_vastu.architectural_intelligence.providers.base import ArchitecturalReasoningInput
from ai_vastu.architectural_intelligence.providers.nvidia_nim import (
    build_nvidia_nim_architectural_intelligence_for_test,
)
from ai_vastu.architectural_intelligence.service import (
    create_architectural_intelligence_provider,
)
from ai_vastu.nvidia_nim_http import PRIMARY_TEXT_MODEL
from ai_vastu.requirements.models import ConfirmedRequirements, Direction
from ai_vastu.requirements.providers.base import InterpretationInput, ReferenceAsset
from ai_vastu.requirements.providers.nvidia_nim import (
    build_nvidia_nim_requirements_provider_for_test,
)
from ai_vastu.requirements.service import create_provider
from ai_vastu.vastu_reasoning.catalog import load_soft_vastu_catalog
from ai_vastu.vastu_reasoning.providers.base import VastuReasoningInput
from ai_vastu.vastu_reasoning.providers.nvidia_nim import (
    build_nvidia_nim_vastu_provider_for_test,
)
from ai_vastu.vastu_reasoning.service import create_vastu_reasoning_provider

DRAFT = UUID("10000000-0000-0000-0000-000000000029")
USER = UUID("20000000-0000-0000-0000-000000000029")
PROJECT = UUID("30000000-0000-0000-0000-000000000029")


def _response(payload: dict[str, object]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": PRIMARY_TEXT_MODEL,
            "choices": [{"message": {"content": json.dumps(payload)}}],
        },
    )


def _confirmed() -> ConfirmedRequirements:
    return ConfirmedRequirements(
        draft_id=DRAFT,
        user_id=USER,
        project_id=PROJECT,
        user_confirmed=True,
        plot_width_mm=9000,
        plot_depth_mm=15000,
        north_rotation_deg=0,
        road_side=Direction.E,
        floor_count=1,
        bedroom_count=2,
    )


def test_requirements_adapter_validates_schema_and_restores_authority() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return _response(
            {
                "schema_version": "24A.1",
                "draft_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "user_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "project_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "prompt": "untrusted",
                "plot_width_mm": {
                    "value": 9000,
                    "source": "model_inference",
                    "confidence": 0.8,
                    "requires_confirmation": True,
                },
                "plot_depth_mm": None,
                "north_rotation_deg": None,
                "road_side": None,
                "entrance_facing": None,
                "floor_count": None,
                "bedroom_count": None,
                "parking_count": None,
                "vastu_mode": "balanced",
                "rooms": [],
                "questions": ["Confirm plot depth."],
                "warnings": [],
                "reference_names": [],
                "provider": "untrusted",
                "model": "untrusted",
            }
        )

    provider = build_nvidia_nim_requirements_provider_for_test(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    draft = provider.interpret(
        InterpretationInput(
            draft_id=DRAFT,
            user_id=USER,
            project_id=PROJECT,
            prompt="Plan a compact 2BHK.",
            references=(
                ReferenceAsset(
                    filename="reference.png",
                    content_type="image/png",
                    data=b"private-image-bytes",
                ),
            ),
        )
    )

    assert draft.provider == "nvidia_nim"
    assert draft.model == PRIMARY_TEXT_MODEL
    assert draft.draft_id == DRAFT
    assert draft.plot_width_mm is not None
    assert draft.plot_width_mm.requires_confirmation is True
    serialized_request = json.dumps(seen)
    assert "private-image-bytes" not in serialized_request
    assert seen["model"] == PRIMARY_TEXT_MODEL


def test_architectural_adapter_returns_hashed_advisory_intent() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return _response(
            {
                "strategy_summary": "Compact functional zoning for solver evaluation.",
                "room_intents": [],
                "relationships": [],
                "circulation": {
                    "preferred_entry_room_types": [],
                    "avoid_direct_view_to_room_types": [],
                    "minimize_dead_end_corridors": True,
                    "minimize_internal_travel": True,
                    "notes": [],
                },
                "planning_notes": ["Advisory only."],
                "warnings": [],
            }
        )

    source = _confirmed()
    provider = build_nvidia_nim_architectural_intelligence_for_test(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    intent = provider.reason(
        ArchitecturalReasoningInput(
            confirmed=source,
            original_prompt="Plan a compact 2BHK.",
        )
    )

    assert intent.provider == "nvidia_nim"
    assert intent.model == PRIMARY_TEXT_MODEL
    assert intent.project_id == PROJECT
    assert intent.content_hash == intent.compute_content_hash()


def test_vastu_adapter_returns_hashed_soft_profile() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return _response({"rules": [], "notes": ["Soft influence only."]})

    source = _confirmed()
    provider = build_nvidia_nim_vastu_provider_for_test(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    )
    profile = provider.reason(
        VastuReasoningInput(
            confirmed=source,
            original_prompt="Plan a balanced home.",
            catalog=load_soft_vastu_catalog(),
        )
    )

    assert profile.provider == "nvidia_nim"
    assert profile.model == PRIMARY_TEXT_MODEL
    assert profile.project_id == PROJECT
    assert profile.content_hash == profile.compute_content_hash()


def test_all_three_factories_select_nvidia_without_legacy_credentials(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "secret")
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PROVIDER", "nvidia_nim")
    monkeypatch.setenv("AI_VASTU_ARCHITECT_PROVIDER", "nvidia_nim")
    monkeypatch.setenv("AI_VASTU_VASTU_PROVIDER", "nvidia_nim")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert create_provider().name == "nvidia_nim"
    assert create_architectural_intelligence_provider().name == "nvidia_nim"
    assert create_vastu_reasoning_provider().name == "nvidia_nim"


def test_architectural_brain_factory_selects_nvidia_without_legacy_credentials(
    monkeypatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "secret")
    monkeypatch.setenv("AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER", "nvidia_nim")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    provider = create_architectural_brain_provider()

    assert isinstance(provider, NvidiaNimArchitecturalBrainProvider)


def test_revision_router_selects_only_nvidia_adapter(monkeypatch) -> None:
    from ai_vastu.architectural_brain import nvidia_nim_revision

    sentinel = object()
    received: dict[str, object] = {}

    def fake_interpret(**kwargs):
        received.update(kwargs)
        return sentinel

    monkeypatch.setenv("AI_VASTU_REVISION_PROVIDER", "nvidia_nim")
    monkeypatch.setattr(
        nvidia_nim_revision,
        "interpret_revision_with_nvidia_nim",
        fake_interpret,
    )

    result = interpret_revision(
        project_id=PROJECT,
        base_revision_id=DRAFT,
        request="Move the kitchen east.",
    )

    assert result is sentinel
    assert received == {
        "project_id": PROJECT,
        "base_revision_id": DRAFT,
        "request": "Move the kitchen east.",
    }
