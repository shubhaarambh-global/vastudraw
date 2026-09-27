from __future__ import annotations

import json
from collections.abc import Iterator

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
    OpenRouterRequestError,
    image_url_part,
    pdf_file_part,
)
from ai_vastu.provider_runtime import (
    MAX_PROVIDER_RESPONSE_BYTES,
    ProviderBudget,
    ProviderFailureCategory,
)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class _OversizedChunkStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b"x" * MAX_PROVIDER_RESPONSE_BYTES
        yield b"x"


class _LateChunkStream(httpx.SyncByteStream):
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def __iter__(self) -> Iterator[bytes]:
        self._clock.now = 6.0
        yield b'{"choices":[{"message":{"content":"{\\"ok\\":true}"}}]}'


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


@pytest.mark.parametrize(
    ("status_code", "category"),
    (
        (400, ProviderFailureCategory.REQUEST_REJECTED),
        (401, ProviderFailureCategory.AUTHENTICATION),
        (403, ProviderFailureCategory.AUTHENTICATION),
        (404, ProviderFailureCategory.REQUEST_REJECTED),
        (405, ProviderFailureCategory.REQUEST_REJECTED),
        (413, ProviderFailureCategory.REQUEST_REJECTED),
        (415, ProviderFailureCategory.REQUEST_REJECTED),
        (422, ProviderFailureCategory.REQUEST_REJECTED),
    ),
)
def test_non_retryable_status_fails_fast_and_sanitized(
    status_code: int,
    category: ProviderFailureCategory,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status_code,
            json={"error": {"message": "prompt and secret-key"}},
        )

    client = OpenRouterClient(
        api_key="secret-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OpenRouterRequestError) as raised:
        client.complete_validated_json(
            messages=({"role": "user", "content": "private prompt"},),
            models=OpenRouterModelPolicy().reasoning_chain,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert calls == 1
    assert raised.value.category is category
    assert str(raised.value) == f"openrouter request failed ({category.value})."
    assert "secret-key" not in str(raised.value)
    assert "private prompt" not in str(raised.value)


@pytest.mark.parametrize("status_code", (408, 429, 500, 502, 503, 504, 599))
def test_transient_status_uses_exact_fallback_once(status_code: int) -> None:
    models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = str(json.loads(request.content)["model"])
        models.append(model)
        if len(models) == 1:
            return httpx.Response(status_code, json={"error": "do not expose"})
        return _response('{"ok": true}')

    result = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=OpenRouterModelPolicy().reasoning_chain,
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )

    assert result == {"ok": True}
    assert models == [PRIMARY_ARCHITECTURAL_MODEL, FALLBACK_REASONING_MODEL]


@pytest.mark.parametrize(
    ("status_code", "category"),
    (
        (408, ProviderFailureCategory.TIMEOUT),
        (429, ProviderFailureCategory.RATE_LIMITED),
        (500, ProviderFailureCategory.UNAVAILABLE),
        (504, ProviderFailureCategory.TIMEOUT),
    ),
)
def test_final_fallback_failure_has_typed_category(
    status_code: int,
    category: ProviderFailureCategory,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, text="raw provider secret")

    client = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OpenRouterRequestError) as raised:
        client.complete_validated_json(
            messages=({"role": "user", "content": "private prompt"},),
            models=OpenRouterModelPolicy().reasoning_chain,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert calls == 2
    assert raised.value.category is category
    assert "raw provider secret" not in str(raised.value)


@pytest.mark.parametrize(
    "failure_type",
    (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError),
)
def test_eligible_transport_failure_uses_fallback(
    failure_type: type[httpx.TransportError],
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise failure_type("transport secret", request=request)
        return _response('{"ok": true}')

    result = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=OpenRouterModelPolicy().reasoning_chain,
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )

    assert calls == 2
    assert result == {"ok": True}


def test_local_protocol_failure_does_not_use_fallback() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.LocalProtocolError("local request defect", request=request)

    client = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OpenRouterRequestError) as raised:
        client.complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=OpenRouterModelPolicy().reasoning_chain,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert calls == 1
    assert raised.value.category is ProviderFailureCategory.UNAVAILABLE


def test_invalid_fallback_response_is_sanitized_and_typed() -> None:
    client = OpenRouterClient(
        api_key="secret-key",
        transport=httpx.MockTransport(lambda _request: _response("private prompt")),
    )

    with pytest.raises(OpenRouterRequestError) as raised:
        client.complete_validated_json(
            messages=({"role": "user", "content": "private prompt"},),
            models=OpenRouterModelPolicy().reasoning_chain,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert raised.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert str(raised.value) == "openrouter request failed (invalid_response)."


@pytest.mark.parametrize(
    "models",
    (
        (),
        (PRIMARY_ARCHITECTURAL_MODEL, PRIMARY_ARCHITECTURAL_MODEL),
        (PRIMARY_ARCHITECTURAL_MODEL, VISION_PLAN_MODEL),
        (FALLBACK_REASONING_MODEL, PRIMARY_ARCHITECTURAL_MODEL),
    ),
)
def test_only_exact_pinned_attempt_chains_are_accepted(models: tuple[str, ...]) -> None:
    client = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(lambda _request: _response('{"ok": true}')),
    )

    with pytest.raises(OpenRouterConfigurationError, match="exact approved pinned chain"):
        client.complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=models,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )


@pytest.mark.parametrize(
    "model",
    (PRIMARY_ARCHITECTURAL_MODEL, FALLBACK_REASONING_MODEL, VISION_PLAN_MODEL),
)
def test_explicit_qualified_singleton_probe_remains_compatible(model: str) -> None:
    requested_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_models.append(str(json.loads(request.content)["model"]))
        return _response('{"ok": true}')

    result = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "qualification probe"},),
        models=(model,),
        validator=lambda payload, used_model: (payload, used_model),
        temperature=0.0,
    )

    assert result == ({"ok": True}, model)
    assert requested_models == [model]


def test_unapproved_singleton_probe_is_rejected_before_http() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response('{"ok": true}')

    client = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(OpenRouterConfigurationError, match="non-approved or non-free"):
        client.complete_validated_json(
            messages=({"role": "user", "content": "qualification probe"},),
            models=("random/model:free",),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert calls == 0


def test_shared_total_budget_prevents_fallback_after_deadline() -> None:
    clock = Clock()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        clock.now = 5.0
        return httpx.Response(503, json={"error": "late"})

    client = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        budget=ProviderBudget(
            attempt_timeout_seconds=2.0,
            total_timeout_seconds=4.0,
            retry_delay_seconds=0.0,
            max_retry_after_seconds=0.0,
        ),
        monotonic=clock,
    )

    with pytest.raises(OpenRouterRequestError) as raised:
        client.complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=OpenRouterModelPolicy().reasoning_chain,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert calls == 1
    assert raised.value.category is ProviderFailureCategory.TIMEOUT


def test_each_attempt_timeout_is_capped_by_remaining_total_budget() -> None:
    clock = Clock()
    timeouts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeout = request.extensions["timeout"]
        assert isinstance(timeout, dict)
        timeouts.append(float(timeout["read"]))
        if len(timeouts) == 1:
            clock.now = 3.0
            return httpx.Response(503, json={"error": "retry"})
        return _response('{"ok": true}')

    result = OpenRouterClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        budget=ProviderBudget(
            attempt_timeout_seconds=4.0,
            total_timeout_seconds=5.0,
            retry_delay_seconds=0.0,
            max_retry_after_seconds=0.0,
        ),
        monotonic=clock,
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=OpenRouterModelPolicy().reasoning_chain,
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )

    assert result == {"ok": True}
    assert timeouts == [4.0, 2.0]


@pytest.mark.parametrize("declared", (True, False))
def test_oversized_provider_response_is_rejected_without_fallback(
    declared: bool,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        if declared:
            return httpx.Response(
                200,
                headers={"Content-Length": str(MAX_PROVIDER_RESPONSE_BYTES + 1)},
                content=b"{}",
            )
        return httpx.Response(200, stream=_OversizedChunkStream())

    with pytest.raises(OpenRouterRequestError) as raised:
        OpenRouterClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_ARCHITECTURAL_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert raised.value.category is ProviderFailureCategory.INVALID_RESPONSE


def test_total_deadline_is_enforced_while_streaming_response() -> None:
    clock = Clock()

    with pytest.raises(OpenRouterRequestError) as raised:
        OpenRouterClient(
            api_key="test-key",
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, stream=_LateChunkStream(clock))
            ),
            budget=ProviderBudget(
                attempt_timeout_seconds=4.0,
                total_timeout_seconds=5.0,
                retry_delay_seconds=0.0,
                max_retry_after_seconds=0.0,
            ),
            monotonic=clock,
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_ARCHITECTURAL_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert raised.value.category is ProviderFailureCategory.TIMEOUT
