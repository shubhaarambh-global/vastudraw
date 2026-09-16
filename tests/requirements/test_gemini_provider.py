import json
from uuid import UUID, uuid4

import httpx

from ai_vastu.requirements.providers.base import InterpretationInput, ReferenceAsset
from ai_vastu.requirements.providers.gemini_generate_content import (
    GeminiGenerateContentRequirementsProvider,
)

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")


def _draft_payload() -> dict[str, object]:
    return {
        "schema_version": "24A.1",
        "draft_id": "bad-model-id",
        "user_id": "bad-model-id",
        "project_id": "bad-model-id",
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


def test_gemini_provider_uses_structured_json_and_restores_identity() -> None:
    draft_id = uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "test-key"
        assert request.url.path.endswith("/models/gemini-2.5-flash:generateContent")
        body = json.loads(request.content)
        config = body["generationConfig"]
        assert config["responseMimeType"] == "application/json"
        assert "responseJsonSchema" in config
        assert body["contents"][0]["parts"][1]["inlineData"]["mimeType"] == "image/png"
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": json.dumps(_draft_payload())}]
                        }
                    }
                ]
            },
        )

    provider = GeminiGenerateContentRequirementsProvider(
        api_key="test-key",
        model="gemini-2.5-flash",
        transport=httpx.MockTransport(handler),
    )
    request = InterpretationInput(
        draft_id=draft_id,
        user_id=USER,
        project_id=PROJECT,
        prompt="30 x 50 ft east road",
        references=(
            ReferenceAsset(
                filename="plan.png",
                content_type="image/png",
                data=b"fake-png-for-mock",
            ),
        ),
    )
    draft = provider.interpret(request)

    assert draft.draft_id == draft_id
    assert draft.user_id == USER
    assert draft.project_id == PROJECT
    assert draft.prompt == request.prompt
    assert draft.provider == "gemini"
    assert draft.model == "gemini-2.5-flash"
    assert draft.reference_names == ["plan.png"]
