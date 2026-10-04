from __future__ import annotations

import inspect
import json
from collections.abc import Iterator

import httpx
import pytest

from ai_vastu.nvidia_nim_http import (
    INACTIVE_UNQUALIFIED_TEXT_MODEL,
    NVIDIA_NIM_API_BASE,
    NVIDIA_NIM_PROVIDER,
    PRIMARY_TEXT_MODEL,
    VISION_MODEL,
    NvidiaNimClient,
    NvidiaNimConfigurationError,
    NvidiaNimFailureStage,
    NvidiaNimModelPolicy,
    NvidiaNimRequestError,
    image_url_part,
    schema_instruction,
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
        yield b"{}"


class _MislabeledDeflateStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b'{"choices":[]}'


def _response(content: str, *, model: str = PRIMARY_TEXT_MODEL) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "sanitized",
            "model": model,
            "choices": [{"message": {"role": "assistant", "content": content}}],
        },
    )


def test_constants_and_default_policy_are_exactly_pinned() -> None:
    policy = NvidiaNimModelPolicy()

    assert NVIDIA_NIM_PROVIDER == "nvidia_nim"
    assert NVIDIA_NIM_API_BASE == "https://integrate.api.nvidia.com/v1"
    assert policy.text_chain == (PRIMARY_TEXT_MODEL,)
    assert policy.vision_chain == (VISION_MODEL,)
    assert PRIMARY_TEXT_MODEL == "nvidia/nemotron-3-ultra-550b-a55b"
    assert INACTIVE_UNQUALIFIED_TEXT_MODEL == "nvidia/nemotron-3.5-lightning-30b-a3b"
    assert VISION_MODEL == "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


@pytest.mark.parametrize(
    ("name", "value"),
    (
        ("AI_VASTU_NVIDIA_PRIMARY_MODEL", INACTIVE_UNQUALIFIED_TEXT_MODEL),
        ("AI_VASTU_NVIDIA_FALLBACK_MODEL", INACTIVE_UNQUALIFIED_TEXT_MODEL),
        ("AI_VASTU_NVIDIA_VISION_MODEL", "nvidia/random-model"),
    ),
)
def test_model_environment_cannot_repin_an_approved_role(
    name: str,
    value: str,
) -> None:
    with pytest.raises(NvidiaNimConfigurationError, match=r"must remain pinned|inactive"):
        NvidiaNimModelPolicy.from_environment({name: value})


def test_environment_requires_only_nvidia_key_and_pinned_base() -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        assert request.headers["Authorization"] == "Bearer nvidia-test-key"
        return _response('{"ok":true}')

    client = NvidiaNimClient.from_environment(
        {
            "NVIDIA_API_KEY": "nvidia-test-key",
            "AI_VASTU_NVIDIA_BASE_URL": NVIDIA_NIM_API_BASE,
        },
        transport=httpx.MockTransport(handler),
    )
    result = client.complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=(PRIMARY_TEXT_MODEL,),
        validator=lambda payload, model: (payload, model),
        temperature=0.0,
    )

    assert result == ({"ok": True}, PRIMARY_TEXT_MODEL)
    assert requested_urls == [f"{NVIDIA_NIM_API_BASE}/chat/completions"]


def test_nano_omni_request_can_only_send_fixed_thinking_disabled_control() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _response('{"ok":true}', model=VISION_MODEL)

    result = NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=(VISION_MODEL,),
        validator=lambda payload, _model: payload,
        temperature=0.1,
        max_tokens=4096,
        disable_thinking=True,
    )

    assert result == {"ok": True}
    assert bodies[0]["chat_template_kwargs"] == {"enable_thinking": False}
    assert "response_format" not in bodies[0]


def test_thinking_control_has_no_arbitrary_override_surface() -> None:
    parameters = inspect.signature(
        NvidiaNimClient.complete_validated_json
    ).parameters
    assert "extra_body" not in parameters
    assert "chat_template_kwargs" not in parameters

    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response('{"ok":true}')

    client = NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )
    for models, value in (
        ((PRIMARY_TEXT_MODEL,), True),
        ((VISION_MODEL,), 1),
        ((VISION_MODEL,), {"enable_thinking": True}),
    ):
        with pytest.raises(NvidiaNimConfigurationError):
            client.complete_validated_json(
                messages=({"role": "user", "content": "return JSON"},),
                models=models,
                validator=lambda payload, _model: payload,
                temperature=0.0,
                disable_thinking=value,  # type: ignore[arg-type]
            )

    assert calls == 0


def test_ultra_request_body_remains_unchanged_without_thinking_control() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _response('{"ok":true}')

    NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=(PRIMARY_TEXT_MODEL,),
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )

    assert set(bodies[0]) == {"model", "messages", "temperature"}
    assert "chat_template_kwargs" not in bodies[0]


def test_model_inventory_verifies_all_exact_pins_before_completions() -> None:
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url)))
        assert request.headers["Authorization"] == "Bearer nvidia-test-key"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"id": PRIMARY_TEXT_MODEL},
                    {"id": VISION_MODEL},
                    {"id": "unrelated/model"},
                ]
            },
        )

    verified = NvidiaNimClient(
        api_key="nvidia-test-key",
        transport=httpx.MockTransport(handler),
    ).verify_pinned_models_available()

    assert verified == (PRIMARY_TEXT_MODEL, VISION_MODEL)
    assert requests == [("GET", f"{NVIDIA_NIM_API_BASE}/models")]


@pytest.mark.parametrize(
    "response",
    (
        *(
            httpx.Response(
                200,
                json={
                    "data": [
                        {"id": candidate}
                        for candidate in (
                            PRIMARY_TEXT_MODEL,
                            VISION_MODEL,
                        )
                        if candidate != missing
                    ]
                },
            )
            for missing in (PRIMARY_TEXT_MODEL, VISION_MODEL)
        ),
        httpx.Response(
            200,
            json={
                "data": [
                    {"id": PRIMARY_TEXT_MODEL.upper()},
                    {"id": VISION_MODEL + "-alias"},
                ]
            },
        ),
        httpx.Response(200, json={"data": "not-a-list"}),
        httpx.Response(200, json={"data": [{"name": PRIMARY_TEXT_MODEL}]}),
        httpx.Response(200, content=b"not-json"),
    ),
)
def test_model_inventory_fails_closed_on_missing_or_malformed_catalog(
    response: httpx.Response,
) -> None:
    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(lambda _request: response),
        ).verify_pinned_models_available()

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE


@pytest.mark.parametrize(
    ("status", "category"),
    (
        (401, ProviderFailureCategory.AUTHENTICATION),
        (403, ProviderFailureCategory.AUTHENTICATION),
        (408, ProviderFailureCategory.TIMEOUT),
        (429, ProviderFailureCategory.RATE_LIMITED),
        (500, ProviderFailureCategory.UNAVAILABLE),
        (504, ProviderFailureCategory.TIMEOUT),
    ),
)
def test_model_inventory_http_failures_are_typed_and_sanitized(
    status: int,
    category: ProviderFailureCategory,
) -> None:
    secret = "inventory-secret"
    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key=secret,
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(status, text="provider-secret-body")
            ),
        ).verify_pinned_models_available()

    assert captured.value.category is category
    assert secret not in str(captured.value)
    assert "provider-secret-body" not in str(captured.value)


@pytest.mark.parametrize("declared", (True, False))
def test_model_inventory_response_cap_is_enforced(declared: bool) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        if declared:
            return httpx.Response(
                200,
                headers={"Content-Length": str(MAX_PROVIDER_RESPONSE_BYTES + 1)},
                content=b"{}",
            )
        return httpx.Response(200, stream=_OversizedChunkStream())

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).verify_pinned_models_available()

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE


def test_missing_key_and_unpinned_base_are_rejected_without_secret_leak() -> None:
    with pytest.raises(NvidiaNimConfigurationError, match="NVIDIA_API_KEY"):
        NvidiaNimClient.from_environment({})

    secret = "nvidia-secret-value"
    with pytest.raises(NvidiaNimConfigurationError) as captured:
        NvidiaNimClient(
            api_key=secret,
            base_url="https://attacker.example/v1",
        )
    assert secret not in str(captured.value)


@pytest.mark.parametrize(
    "models",
    (
        (),
        (PRIMARY_TEXT_MODEL, PRIMARY_TEXT_MODEL),
        (PRIMARY_TEXT_MODEL, VISION_MODEL),
        (INACTIVE_UNQUALIFIED_TEXT_MODEL,),
        ("nvidia/random-model",),
    ),
)
def test_only_exact_pinned_attempt_chains_are_allowed(
    models: tuple[str, ...],
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response('{"ok":true}')

    with pytest.raises(NvidiaNimConfigurationError, match="exact approved pinned chain"):
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=models,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )
    assert calls == 0


@pytest.mark.parametrize(
    "model",
    (PRIMARY_TEXT_MODEL, VISION_MODEL),
)
def test_each_approved_model_can_be_qualified_as_an_exact_singleton(
    model: str,
) -> None:
    requested_models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_models.append(str(json.loads(request.content)["model"]))
        return _response('{"ok":true}', model=model)

    result = NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "qualification"},),
        models=(model,),
        validator=lambda payload, used_model: (payload, used_model),
        temperature=0.0,
    )

    assert result == ({"ok": True}, model)
    assert requested_models == [model]


@pytest.mark.parametrize(
    ("requested", "reported"),
    (
        (PRIMARY_TEXT_MODEL, None),
        (PRIMARY_TEXT_MODEL, PRIMARY_TEXT_MODEL.upper()),
        (VISION_MODEL, VISION_MODEL + "-alias"),
        (VISION_MODEL, PRIMARY_TEXT_MODEL),
    ),
)
def test_completion_response_must_report_the_exact_requested_model(
    requested: str,
    reported: str | None,
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        payload: dict[str, object] = {
            "choices": [{"message": {"content": '{"ok":true}'}}]
        }
        if reported is not None:
            payload["model"] = reported
        return httpx.Response(200, json=payload)

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "qualification"},),
            models=(requested,),
            validator=lambda payload, used_model: (payload, used_model),
            temperature=0.0,
        )

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert captured.value.stage is NvidiaNimFailureStage.PROVENANCE


def test_ultra_omits_unsupported_response_format() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        return _response('{"ok":true}', model=PRIMARY_TEXT_MODEL)

    result = NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=NvidiaNimModelPolicy().text_chain,
        validator=lambda payload, _model: payload,
        temperature=0.0,
        max_tokens=512,
        response_format={"type": "json_object"},
    )

    assert result == {"ok": True}
    assert "response_format" not in bodies[0]
    assert [body["model"] for body in bodies] == [PRIMARY_TEXT_MODEL]
    assert [body["max_tokens"] for body in bodies] == [512]


def test_unsupported_response_format_is_rejected_before_http() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response('{"ok":true}')

    with pytest.raises(NvidiaNimConfigurationError, match="json_object"):
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
            response_format={"type": "json_schema"},
        )
    assert calls == 0


@pytest.mark.parametrize("max_tokens", (True, 0, -1, 1.5))
def test_invalid_max_tokens_is_rejected_before_http(max_tokens: object) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response('{"ok":true}')

    with pytest.raises(NvidiaNimConfigurationError, match="positive integer"):
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
            max_tokens=max_tokens,  # type: ignore[arg-type]
        )
    assert calls == 0


@pytest.mark.parametrize(
    "content",
    (
        '<think>private reasoning</think>\n{"ok":true}',
        '```json\n{"ok":true}\n```',
        'prefix {"ok":true}',
        '{"ok":true} suffix',
        "[]",
    ),
)
def test_markdown_prose_and_non_object_json_are_rejected(content: str) -> None:
    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="secret-key",
            transport=httpx.MockTransport(lambda _request: _response(content)),
        ).complete_validated_json(
            messages=({"role": "user", "content": "private prompt"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert str(captured.value) == "nvidia_nim request failed (invalid_response)."
    assert "secret-key" not in str(captured.value)
    assert "private prompt" not in str(captured.value)


@pytest.mark.parametrize(
    "response",
    (
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": 7}}]}),
    ),
)
def test_malformed_provider_envelopes_are_invalid_response(
    response: httpx.Response,
) -> None:
    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(lambda _request: response),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE


def test_application_validator_failure_is_not_retried() -> None:
    models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = str(json.loads(request.content)["model"])
        models.append(model)
        return _response('{"requirement":"invalid"}', model=model)

    def validator(payload: dict[str, object], model: str) -> str:
        if payload.get("requirement") != "valid":
            raise ValueError("RequirementDraft rejected")
        return model

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "requirements"},),
            models=NvidiaNimModelPolicy().text_chain,
            validator=validator,
            temperature=0.0,
        )

    assert captured.value.stage is NvidiaNimFailureStage.APPLICATION_VALIDATION
    assert models == [PRIMARY_TEXT_MODEL]


def test_nano_transient_retry_preserves_fixed_thinking_control() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx.Response(503)
        return _response('{"ok":true}', model=VISION_MODEL)

    result = NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=(VISION_MODEL,),
        validator=lambda payload, _model: payload,
        temperature=0.1,
        disable_thinking=True,
    )

    assert result == {"ok": True}
    assert len(bodies) == 2
    assert all(
        body["chat_template_kwargs"] == {"enable_thinking": False}
        for body in bodies
    )


@pytest.mark.parametrize(
    ("status_code", "category"),
    (
        (400, ProviderFailureCategory.REQUEST_REJECTED),
        (401, ProviderFailureCategory.AUTHENTICATION),
        (403, ProviderFailureCategory.AUTHENTICATION),
        (404, ProviderFailureCategory.REQUEST_REJECTED),
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
            json={"error": "provider secret and private prompt"},
        )

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="secret-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "private prompt"},),
            models=NvidiaNimModelPolicy().text_chain,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert calls == 1
    assert captured.value.category is category
    assert captured.value.http_status == status_code
    assert str(captured.value) == f"nvidia_nim request failed ({category.value})."
    assert "secret-key" not in str(captured.value)
    assert "private prompt" not in str(captured.value)


@pytest.mark.parametrize("status_code", (408, 500, 502, 503, 504, 599))
def test_transient_status_retries_exact_same_model_once(status_code: int) -> None:
    models: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = str(json.loads(request.content)["model"])
        models.append(model)
        if len(models) == 1:
            return httpx.Response(status_code, text="provider secret")
        return _response('{"ok":true}', model=model)

    result = NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=NvidiaNimModelPolicy().text_chain,
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )

    assert result == {"ok": True}
    assert models == [PRIMARY_TEXT_MODEL, PRIMARY_TEXT_MODEL]


@pytest.mark.parametrize(
    ("status_code", "category"),
    (
        (408, ProviderFailureCategory.TIMEOUT),
        (429, ProviderFailureCategory.RATE_LIMITED),
        (500, ProviderFailureCategory.UNAVAILABLE),
        (504, ProviderFailureCategory.TIMEOUT),
    ),
)
def test_final_failure_has_typed_category(
    status_code: int,
    category: ProviderFailureCategory,
) -> None:
    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(status_code, text="secret")
            ),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert captured.value.category is category
    assert captured.value.http_status == status_code
    assert "secret" not in str(captured.value)


@pytest.mark.parametrize(
    "failure_type",
    (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError),
)
def test_eligible_transport_failure_retries_same_model(
    failure_type: type[httpx.TransportError],
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise failure_type("transport secret", request=request)
        return _response('{"ok":true}', model=PRIMARY_TEXT_MODEL)

    result = NvidiaNimClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return JSON"},),
        models=NvidiaNimModelPolicy().text_chain,
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )

    assert calls == 2
    assert result == {"ok": True}


def test_local_protocol_failure_does_not_fallback() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.LocalProtocolError("local defect", request=request)

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=NvidiaNimModelPolicy().text_chain,
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert calls == 1
    assert captured.value.category is ProviderFailureCategory.UNAVAILABLE


@pytest.mark.parametrize("declared", (True, False))
def test_two_mib_response_cap_is_enforced(declared: bool) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        if declared:
            return httpx.Response(
                200,
                headers={"Content-Length": str(MAX_PROVIDER_RESPONSE_BYTES + 1)},
                content=b"{}",
            )
        return httpx.Response(200, stream=_OversizedChunkStream())

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE


def test_content_decoding_failure_is_invalid_response() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Encoding": "deflate"},
            stream=_MislabeledDeflateStream(),
        )

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="test-key",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return JSON"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE


def test_total_deadline_is_enforced_while_streaming() -> None:
    clock = Clock()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, stream=_LateChunkStream(clock))

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
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
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0.0,
        )

    assert captured.value.category is ProviderFailureCategory.TIMEOUT
    assert calls == 1


def test_each_attempt_is_capped_by_remaining_total_budget() -> None:
    clock = Clock()
    timeouts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeout = request.extensions["timeout"]
        assert isinstance(timeout, dict)
        timeouts.append(float(timeout["read"]))
        if len(timeouts) == 1:
            clock.now = 3.0
            return httpx.Response(503)
        return _response('{"ok":true}', model=PRIMARY_TEXT_MODEL)

    result = NvidiaNimClient(
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
        models=NvidiaNimModelPolicy().text_chain,
        validator=lambda payload, _model: payload,
        temperature=0.0,
    )

    assert result == {"ok": True}
    assert timeouts == [4.0, 2.0]


def test_image_helper_accepts_only_png_and_jpeg() -> None:
    png = image_url_part("image/png", b"png")
    jpeg = image_url_part("image/jpeg", b"jpeg")

    assert str(png["image_url"]["url"]).startswith("data:image/png;base64,")
    assert str(jpeg["image_url"]["url"]).startswith("data:image/jpeg;base64,")
    with pytest.raises(ValueError, match="Unsupported NVIDIA NIM image"):
        image_url_part("image/webp", b"webp")
    with pytest.raises(ValueError, match="Unsupported NVIDIA NIM image"):
        image_url_part("application/pdf", b"pdf")


def test_schema_instruction_demands_strict_unwrapped_json() -> None:
    instruction = schema_instruction({"type": "object", "required": ["rooms"]})

    assert "one JSON object only" in instruction
    assert "Do not wrap it in markdown or add prose" in instruction
    assert '"required":["rooms"]' in instruction
