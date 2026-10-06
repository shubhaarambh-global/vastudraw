from __future__ import annotations

import json
from copy import deepcopy
from typing import Any
from uuid import UUID

import httpx
import pytest

from ai_vastu.architectural_brain.errors import ArchitecturalBrainProviderError
from ai_vastu.architectural_brain.models import ArchitecturalConcept
from ai_vastu.architectural_brain.ollama_local_provider import (
    OllamaLocalArchitecturalBrainProvider,
    _program_output_schema,
)
from ai_vastu.ollama_local_http import OLLAMA_LOCAL_MODEL, OllamaLocalClient
from ai_vastu.provider_runtime import ProviderFailureCategory

PROJECT = UUID("30000000-0000-0000-0000-000000000029")
PROGRAM = ("living", "bedroom", "bedroom", "kitchen", "common_toilet")


def _wire() -> dict[str, Any]:
    return {
        "concepts": [
            {
                "concept_id": "public-core",
                "title": "Living distributes the confirmed program",
                "rooms": [
                    {"room_type": "living", "zone": "PUBLIC"},
                    {"room_type": "bedroom", "zone": "PRIVATE"},
                ],
                "topology": [
                    {
                        "source_room_type": "living",
                        "target_room_type": "bedroom",
                        "relation": "NEAR",
                        "weight": 75,
                    }
                ],
                "design_rationale": ["Keep service spaces compact."],
            }
        ],
    }


def _propose(client: OllamaLocalClient) -> tuple[ArchitecturalConcept, ...]:
    return OllamaLocalArchitecturalBrainProvider(client=client).propose(
        project_id=PROJECT,
        original_prompt="Confirmed compact home.",
        width_mm=9000,
        depth_mm=12000,
        bedroom_count=2,
        toilet_count=1,
        parking_count=0,
        room_types=PROGRAM,
        road_side="E",
        entrance_side="E",
        precedents=(),
        concept_count=2,
    )


def test_brain_decoding_schema_uses_actual_program_not_global_room_enum() -> None:
    public_before = ArchitecturalConcept.model_json_schema()
    schema = _program_output_schema(PROGRAM, 2)
    definitions = schema["$defs"]
    allowed = sorted(set(PROGRAM))
    assert definitions["ConceptRoom"]["properties"]["room_type"]["enum"] == allowed
    for field in ("source_room_type", "target_room_type"):
        assert definitions["TopologyEdge"]["properties"][field]["enum"] == allowed
        assert "dining" not in definitions["TopologyEdge"]["properties"][field]["enum"]
        assert "corridor" not in definitions["TopologyEdge"]["properties"][field]["enum"]
    assert schema["properties"]["concepts"]["minItems"] == 1
    assert schema["properties"]["concepts"]["maxItems"] == 2
    assert definitions["ArchitecturalConcept"]["additionalProperties"] is False
    assert set(definitions["ArchitecturalConcept"]["properties"]) == {
        "concept_id",
        "title",
        "rooms",
        "topology",
        "design_rationale",
    }
    assert ArchitecturalConcept.model_json_schema() == public_before
    # Different client programs must constrain different types without mutation.
    other = _program_output_schema(("living", "dining"), 1)
    assert other["$defs"]["ConceptRoom"]["properties"]["room_type"]["enum"] == ["dining", "living"]
    assert definitions["ConceptRoom"]["properties"]["room_type"]["enum"] == allowed


def test_brain_valid_concept_has_application_identity_authority_and_hash() -> None:
    requests: list[dict[str, Any]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": OLLAMA_LOCAL_MODEL,
                "done": True,
                "message": {"content": json.dumps(_wire())},
            },
        )

    concepts = _propose(OllamaLocalClient(transport=httpx.MockTransport(respond)))
    assert len(requests) == 1
    assert requests[0]["options"]["num_ctx"] == 8192
    assert requests[0]["format"] == _program_output_schema(PROGRAM, 2)
    concept = concepts[0]
    assert concept.project_id == PROJECT
    assert concept.authoritative_geometry is False
    assert concept.precedent_ids == ()
    assert concept.content_hash == concept.compute_content_hash()
    assert ArchitecturalConcept.model_validate_json(concept.model_dump_json()) == concept
    assert concept.topology[0].relation == "NEAR"
    assert concept.topology[0].weight == 75


@pytest.mark.parametrize(
    "defect", ["room", "source", "target", "alias", "excess", "empty", "extra"]
)
def test_brain_schema_ignoring_server_fails_closed_without_retry(defect: str) -> None:
    payload = deepcopy(_wire())
    if defect == "room":
        payload["concepts"][0]["rooms"][0]["room_type"] = "dining"
    elif defect == "source":
        payload["concepts"][0]["topology"][0]["source_room_type"] = "corridor"
    elif defect == "target":
        payload["concepts"][0]["topology"][0]["target_room_type"] = "dining"
    elif defect == "alias":
        payload["concepts"][0]["topology"][0]["target_room_type"] = "bathroom"
    elif defect == "excess":
        payload["concepts"] *= 3
    elif defect == "extra":
        payload["extra"] = "unexpected"
    else:
        payload["concepts"] = []
    calls = 0

    def respond(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "model": OLLAMA_LOCAL_MODEL,
                "done": True,
                "message": {"content": json.dumps(payload)},
            },
        )

    with pytest.raises(ArchitecturalBrainProviderError) as raised:
        _propose(OllamaLocalClient(transport=httpx.MockTransport(respond)))
    assert raised.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert calls == 1


def test_brain_empty_compiled_program_cannot_generate_unknown_rooms() -> None:
    with pytest.raises(ValueError, match="nonempty room program"):
        _program_output_schema((), 1)
