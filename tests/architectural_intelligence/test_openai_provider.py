from __future__ import annotations

import json

import httpx

from ai_vastu.architectural_intelligence import ArchitecturalReasoningInput
from ai_vastu.architectural_intelligence.providers.openai_responses import (
    OpenAIResponsesArchitecturalIntelligenceProvider,
)

from .helpers import confirmed


def test_openai_provider_uses_strict_schema_and_app_owned_identity() -> None:
    source = confirmed()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["text"]["format"]["type"] == "json_schema"
        assert payload["text"]["format"]["strict"] is True
        model_payload = {
            "schema_version": "26A.1",
            "project_id": "ffffffff-ffff-ffff-ffff-ffffffffffff",
            "draft_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "provider": "untrusted",
            "model": "untrusted",
            "strategy_summary": "Functional planning.",
            "room_intents": [],
            "relationships": [],
            "circulation": {
                "preferred_entry_room_types": [],
                "avoid_direct_view_to_room_types": [],
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
            json={
                "output": [
                    {"content": [{"type": "output_text", "text": json.dumps(model_payload)}]}
                ]
            },
        )

    provider = OpenAIResponsesArchitecturalIntelligenceProvider(
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
    assert intent.provider == "openai"
    assert intent.model == "test-model"
