from __future__ import annotations

import json

import httpx
import pytest

from ai_vastu.openrouter_http import (
    FALLBACK_REASONING_MODEL,
    FREE_PDF_PLUGIN,
    PRIMARY_ARCHITECTURAL_MODEL,
    VISION_PLAN_MODEL,
    OpenRouterClient,
    OpenRouterConfigurationError,
    OpenRouterModelPolicy,
    image_url_part,
    pdf_file_part,
)


def _response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content,
                    }
                }
            ]
        },
    )


def test_free_only_policy_is_exact_and_role_pinned() -> None:
    policy = OpenRouterModelPolicy()
    policy.validate()
    assert policy.reasoning_chain == (
        PRIMARY_ARCHITECTURAL_MODEL,
        FALLBACK_REASONING_MODEL,
    )
    assert policy.vision_chain == (VISION_PLAN_MODEL,)

    with pytest.raises(OpenRouterConfigurationError):
        OpenRouterModelPolicy(
            primary="deepseek/deepseek-v4-flash-0731",
            vision=VISION_PLAN_MODEL,
            fallback=FALLBACK_REASONING_MODEL,
        ).validate()


def test_reasoning_falls_back_only_to_approved_free_model() -> None:
    requested_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        model = str(payload["model"])
        requested_models.append(model)
        assert request.headers["Authorization"] == "Bearer test-key"
        if model == PRIMARY_ARCHITECTURAL_MODEL:
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        assert model == FALLBACK_REASONING_MODEL
        return _response('{"ok": true}')

    client = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    result = client.complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=OpenRouterModelPolicy().reasoning_chain,
        validator=lambda payload, model: (payload, model),
        temperature=0.0,
    )

    assert result == ({"ok": True}, FALLBACK_REASONING_MODEL)
    assert requested_models == [
        PRIMARY_ARCHITECTURAL_MODEL,
        FALLBACK_REASONING_MODEL,
    ]


def test_invalid_primary_json_triggers_free_fallback() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        payload = json.loads(request.content.decode("utf-8"))
        if payload["model"] == PRIMARY_ARCHITECTURAL_MODEL:
            return _response("not-json")
        return _response("```json\n{\"value\": 7}\n```")

    client = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    result = client.complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=OpenRouterModelPolicy().reasoning_chain,
        validator=lambda payload, _model: int(payload["value"]),
        temperature=0.0,
    )

    assert result == 7
    assert calls == 2


def test_multimodal_helpers_and_pdf_parser_are_cost_pinned() -> None:
    image = image_url_part("image/png", b"png")
    assert image["type"] == "image_url"
    assert str(image["image_url"]["url"]).startswith("data:image/png;base64,")

    pdf = pdf_file_part("plan.pdf", b"%PDF-1.7")
    assert pdf["type"] == "file"
    assert pdf["file"]["filename"] == "plan.pdf"
    assert str(pdf["file"]["file_data"]).startswith("data:application/pdf;base64,")

    assert FREE_PDF_PLUGIN == (
        {
            "id": "file-parser",
            "pdf": {"engine": "cloudflare-ai"},
        },
    )
