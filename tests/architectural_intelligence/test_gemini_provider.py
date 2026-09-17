from __future__ import annotations

import json

import httpx

from ai_vastu.architectural_intelligence import ArchitecturalReasoningInput
from ai_vastu.architectural_intelligence.providers.gemini import (
    GeminiArchitecturalIntelligenceProvider,
)

from .helpers import confirmed


def test_gemini_provider_uses_structured_output_and_app_owned_identity() -> None:
    source = confirmed()
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        seen["payload"] = payload
        model_payload = {
            "schema_version": "26A.1",
            "project_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "draft_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "provider": "untrusted",
            "model": "untrusted",
            "strategy_summary": "Keep public and service circulation coherent.",
            "room_intents": [],
            "relationships": [],
            "circulation": {
                "preferred_entry_room_types": ["living"],
                "avoid_direct_view_to_room_types": ["common_toilet"],
                "minimize_dead_end_corridors": True,
                "minimize_internal_travel": True,
                "notes": [],
            },
            "planning_notes": [],
            "warnings": [],
            "content_hash": None,
        }
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(model_payload)}]}}]},
        )

    provider = GeminiArchitecturalIntelligenceProvider(
        api_key="test-key",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )
    intent = provider.reason(
        ArchitecturalReasoningInput(
            confirmed=source,
            original_prompt="Plan a practical 2BHK.",
        )
    )

    assert intent.project_id == source.project_id
    assert intent.draft_id == source.draft_id
    assert intent.provider == "gemini"
    assert intent.model == "test-model"
    assert intent.content_hash is not None

    payload = seen["payload"]
    assert isinstance(payload, dict)
    generation_config = payload["generationConfig"]
    assert generation_config["responseMimeType"] == "application/json"
    assert "responseJsonSchema" in generation_config
