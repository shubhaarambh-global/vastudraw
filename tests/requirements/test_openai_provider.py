import json
from uuid import UUID, uuid4

import httpx

from ai_vastu.requirements.providers import (
    InterpretationInput,
    OpenAIResponsesRequirementsProvider,
)

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")


def test_openai_provider_uses_structured_outputs_and_restores_identity() -> None:
    draft_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["store"] is False
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["text"]["format"]["strict"] is True
        payload = {
            "schema_version": "24A.1",
            "draft_id": str(uuid4()),
            "user_id": str(uuid4()),
            "project_id": str(uuid4()),
            "prompt": "model prompt",
            "plot_width_mm": {
                "value": 9144,
                "source": "prompt",
                "confidence": 0.99,
                "requires_confirmation": True,
            },
            "plot_depth_mm": {
                "value": 15240,
                "source": "prompt",
                "confidence": 0.99,
                "requires_confirmation": True,
            },
            "north_rotation_deg": {
                "value": 0,
                "source": "prompt",
                "confidence": 0.99,
                "requires_confirmation": True,
            },
            "road_side": {
                "value": "E",
                "source": "prompt",
                "confidence": 0.99,
                "requires_confirmation": True,
            },
            "entrance_facing": None,
            "floor_count": {
                "value": 1,
                "source": "prompt",
                "confidence": 0.9,
                "requires_confirmation": True,
            },
            "bedroom_count": {
                "value": 2,
                "source": "prompt",
                "confidence": 0.9,
                "requires_confirmation": True,
            },
            "parking_count": {
                "value": 1,
                "source": "prompt",
                "confidence": 0.9,
                "requires_confirmation": True,
            },
            "vastu_mode": "balanced",
            "rooms": [],
            "questions": [],
            "warnings": [],
            "reference_names": [],
            "provider": "model",
            "model": None,
        }
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(payload),
                            }
                        ],
                    }
                ]
            },
        )

    provider = OpenAIResponsesRequirementsProvider(
        api_key="test-key",
        model="test-model",
        transport=httpx.MockTransport(handler),
    )
    request = InterpretationInput(
        draft_id=draft_id,
        user_id=USER,
        project_id=PROJECT,
        prompt="30 x 50 ft east road",
        references=(),
    )
    draft = provider.interpret(request)

    assert draft.draft_id == draft_id
    assert draft.user_id == USER
    assert draft.project_id == PROJECT
    assert draft.prompt == request.prompt
    assert draft.provider == "openai"
    assert draft.model == "test-model"
