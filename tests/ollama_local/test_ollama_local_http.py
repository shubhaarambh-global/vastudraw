from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict

import ai_vastu.ollama_local_http as ollama_http
from ai_vastu.ollama_local_http import (
    DEFAULT_READ_TIMEOUT_SECONDS,
    DEFAULT_TOTAL_TIMEOUT_SECONDS,
    MAX_OLLAMA_REQUEST_BYTES,
    OLLAMA_LOCAL_BASE_URL,
    OLLAMA_LOCAL_MODEL,
    OLLAMA_LOCAL_PROVIDER,
    OllamaLocalClient,
    OllamaLocalConfigurationError,
    OllamaLocalFailureStage,
    OllamaLocalRequestError,
    OllamaLocalTimeoutKind,
    OllamaLocalValidationIssue,
)
from ai_vastu.provider_runtime import MAX_PROVIDER_RESPONSE_BYTES, ProviderFailureCategory

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def _chat_response(
    value: dict[str, Any] | str,
    *,
    model: str = OLLAMA_LOCAL_MODEL,
    done: bool = True,
) -> httpx.Response:
    content = value if isinstance(value, str) else json.dumps(value)
    return httpx.Response(
        200,
        json={
            "model": model,
            "done": done,
            "message": {"role": "assistant", "content": content},
        },
    )


def _complete(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    messages: tuple[dict[str, Any], ...] = ({"role": "user", "content": "hello"},),
    validator: Callable[[dict[str, Any], str], Any] = lambda value, model: (
        value,
        model,
    ),
) -> Any:
    return OllamaLocalClient(
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=messages,
        schema=SCHEMA,
        validator=validator,
    )


def _exception_chain_text(exc: BaseException) -> str:
    messages: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = current.__cause__ or current.__context__
    return " ".join(messages)


def test_identity_and_exact_endpoint_model_policy() -> None:
    assert OLLAMA_LOCAL_PROVIDER == "ollama_local"
    assert OLLAMA_LOCAL_BASE_URL == "http://127.0.0.1:11434"
    assert OLLAMA_LOCAL_MODEL == "qwen3-vl:8b-instruct-q4_K_M"
    assert DEFAULT_READ_TIMEOUT_SECONDS == 300.0
    assert DEFAULT_TOTAL_TIMEOUT_SECONDS == 360.0
    assert isinstance(OllamaLocalClient(base_url=OLLAMA_LOCAL_BASE_URL + "/"), OllamaLocalClient)

    with pytest.raises(OllamaLocalConfigurationError, match="endpoint"):
        OllamaLocalClient(base_url="http://localhost:11434")
    with pytest.raises(OllamaLocalConfigurationError, match="endpoint"):
        OllamaLocalClient(base_url="https://127.0.0.1:11434")
    with pytest.raises(OllamaLocalConfigurationError, match="model"):
        OllamaLocalClient(model="qwen3-vl:latest")


def test_environment_requires_explicit_development_and_exact_pins() -> None:
    client = OllamaLocalClient.from_environment(
        {
            "APP_ENV": "development",
            "AI_VASTU_OLLAMA_BASE_URL": OLLAMA_LOCAL_BASE_URL,
            "AI_VASTU_OLLAMA_MODEL": OLLAMA_LOCAL_MODEL,
        }
    )
    assert isinstance(client, OllamaLocalClient)

    for app_env in ("", "staging", "production"):
        with pytest.raises(OllamaLocalConfigurationError, match="development"):
            OllamaLocalClient.from_environment({"APP_ENV": app_env})
    with pytest.raises(OllamaLocalConfigurationError, match="endpoint"):
        OllamaLocalClient.from_environment(
            {
                "APP_ENV": "development",
                "AI_VASTU_OLLAMA_BASE_URL": "http://192.168.1.5:11434",
            }
        )
    with pytest.raises(OllamaLocalConfigurationError, match="model"):
        OllamaLocalClient.from_environment(
            {"APP_ENV": "development", "AI_VASTU_OLLAMA_MODEL": "another-model"}
        )
    with pytest.raises(OllamaLocalConfigurationError, match="fallback"):
        OllamaLocalClient.from_environment(
            {
                "APP_ENV": "development",
                "AI_VASTU_OLLAMA_FALLBACK_MODEL": OLLAMA_LOCAL_MODEL,
            }
        )


@pytest.mark.parametrize(
    ("keyword", "value"),
    [
        ("connect_timeout_seconds", 10.01),
        ("read_timeout_seconds", 300.01),
        ("total_timeout_seconds", 360.01),
        ("write_timeout_seconds", 60.01),
        ("pool_timeout_seconds", 10.01),
        ("connect_timeout_seconds", float("inf")),
        ("read_timeout_seconds", 0),
    ],
)
def test_timeouts_are_finite_positive_and_capped(keyword: str, value: float) -> None:
    configuration: dict[str, Any] = {keyword: value}
    with pytest.raises(OllamaLocalConfigurationError, match="timeout"):
        OllamaLocalClient(**configuration)


def test_client_disables_proxy_inheritance_and_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    original = httpx.Client

    def client_factory(*args: Any, **kwargs: Any) -> httpx.Client:
        captured.update(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr("ai_vastu.ollama_local_http.httpx.Client", client_factory)
    result = OllamaLocalClient(
        transport=httpx.MockTransport(lambda _request: _chat_response({"answer": "ok"}))
    ).complete_validated_json(
        messages=({"role": "user", "content": "hello"},),
        schema=SCHEMA,
        validator=lambda payload, _model: payload,
    )

    assert result == {"answer": "ok"}
    assert captured["trust_env"] is False
    assert captured["follow_redirects"] is False


def test_chat_request_uses_native_schema_temperature_zero_and_stream_false() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _chat_response({"answer": "ok"})

    result = OllamaLocalClient(
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "hello"},),
        schema=SCHEMA,
        validator=lambda payload, model: (payload, model),
        max_tokens=321,
    )

    assert result == ({"answer": "ok"}, OLLAMA_LOCAL_MODEL)
    assert len(requests) == 1
    assert requests[0].url == f"{OLLAMA_LOCAL_BASE_URL}/api/chat"
    body = json.loads(requests[0].content)
    assert body == {
        "model": OLLAMA_LOCAL_MODEL,
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "format": SCHEMA,
        "options": {"temperature": 0, "num_predict": 321},
    }


def test_failure_is_single_attempt_with_no_model_fallback() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["model"])
        return httpx.Response(503, text="raw provider failure")

    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(handler)

    assert captured.value.category is ProviderFailureCategory.UNAVAILABLE
    assert captured.value.attempts == 1
    assert seen == [OLLAMA_LOCAL_MODEL]


@pytest.mark.parametrize(
    ("content", "stage"),
    [
        ("not json", OllamaLocalFailureStage.STRICT_JSON),
        ("```json\n{}\n```", OllamaLocalFailureStage.STRICT_JSON),
        ('{"answer":"ok"} trailing', OllamaLocalFailureStage.STRICT_JSON),
        ('{"answer":NaN}', OllamaLocalFailureStage.STRICT_JSON),
        ('{"answer":Infinity}', OllamaLocalFailureStage.STRICT_JSON),
        ('{"answer":"one","answer":"two"}', OllamaLocalFailureStage.STRICT_JSON),
        ("[]", OllamaLocalFailureStage.STRICT_JSON),
    ],
)
def test_model_content_must_be_one_strict_json_object(
    content: str,
    stage: OllamaLocalFailureStage,
) -> None:
    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(lambda _request: _chat_response(content))

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert captured.value.stage is stage


@pytest.mark.parametrize(
    "response",
    [
        _chat_response({"answer": "ok"}, model="substituted-model"),
        _chat_response({"answer": "ok"}, done=False),
    ],
)
def test_response_requires_exact_model_and_done_true(response: httpx.Response) -> None:
    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(lambda _request: response)

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert captured.value.stage is OllamaLocalFailureStage.PROVENANCE


def test_application_validator_failure_is_sanitized() -> None:
    sentinel = "private-validator-sentinel"

    def reject(_payload: dict[str, Any], _model: str) -> None:
        raise ValueError(sentinel)

    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(
            lambda _request: _chat_response({"answer": sentinel}),
            validator=reject,
        )

    assert captured.value.stage is OllamaLocalFailureStage.APPLICATION_VALIDATION
    assert captured.value.validation_issues == ()
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    assert sentinel not in _exception_chain_text(captured.value)


def test_pydantic_validation_exposes_only_bounded_allowlisted_issue_metadata() -> None:
    class DiagnosticPayload(BaseModel):
        model_config = ConfigDict(extra="forbid", strict=True)

        rooms: list[int]

    sentinel = "private-validation-input-sentinel"
    payload: dict[str, Any] = {
        "rooms": [sentinel],
        **{f"private-extra-{index}-{sentinel}": index for index in range(12)},
    }

    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(
            lambda _request: _chat_response(payload),
            validator=lambda value, _model: DiagnosticPayload.model_validate(value),
        )

    assert captured.value.stage is OllamaLocalFailureStage.APPLICATION_VALIDATION
    assert len(captured.value.validation_issues) == 8
    assert captured.value.validation_issues[0] == OllamaLocalValidationIssue(
        location="rooms.0",
        error_type="int_type",
    )
    assert all(
        issue.location in {"rooms.0", "<field>"}
        for issue in captured.value.validation_issues
    )
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    diagnostic_text = repr(captured.value.__dict__)
    assert sentinel not in diagnostic_text
    assert sentinel not in _exception_chain_text(captured.value)


def test_endpoint_and_model_availability_use_read_only_apis() -> None:
    methods_and_paths: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods_and_paths.append((request.method, request.url.path))
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.35.0"})
        return httpx.Response(
            200,
            json={"models": [{"name": OLLAMA_LOCAL_MODEL, "model": OLLAMA_LOCAL_MODEL}]},
        )

    client = OllamaLocalClient(transport=httpx.MockTransport(handler))
    assert client.verify_endpoint() == "0.35.0"
    assert client.verify_pinned_model_available() == OLLAMA_LOCAL_MODEL
    assert methods_and_paths == [("GET", "/api/version"), ("GET", "/api/tags")]


def test_missing_pinned_model_is_provenance_failure_and_never_pulls() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"models": [{"name": "qwen3-vl:latest"}]})

    with pytest.raises(OllamaLocalRequestError) as captured:
        OllamaLocalClient(
            transport=httpx.MockTransport(handler)
        ).verify_pinned_model_available()

    assert captured.value.stage is OllamaLocalFailureStage.PROVENANCE
    assert paths == ["/api/tags"]


def test_conflicting_model_inventory_identity_is_rejected() -> None:
    response = {
        "models": [
            {"name": OLLAMA_LOCAL_MODEL, "model": "qwen3-vl:substituted"},
        ]
    }

    with pytest.raises(OllamaLocalRequestError) as captured:
        OllamaLocalClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json=response)
            )
        ).verify_pinned_model_available()

    assert captured.value.stage is OllamaLocalFailureStage.PROVENANCE


@pytest.mark.parametrize(
    ("exception_factory", "category", "timeout_kind"),
    [
        (
            lambda request: httpx.ReadTimeout("secret transport timeout", request=request),
            ProviderFailureCategory.TIMEOUT,
            OllamaLocalTimeoutKind.READ,
        ),
        (
            lambda request: httpx.ConnectTimeout("secret connect timeout", request=request),
            ProviderFailureCategory.TIMEOUT,
            OllamaLocalTimeoutKind.CONNECT,
        ),
        (
            lambda request: httpx.ConnectError("secret unavailable", request=request),
            ProviderFailureCategory.UNAVAILABLE,
            None,
        ),
    ],
)
def test_transport_failures_are_categorized_sanitized_and_not_retried(
    exception_factory: Callable[[httpx.Request], httpx.TransportError],
    category: ProviderFailureCategory,
    timeout_kind: OllamaLocalTimeoutKind | None,
) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise exception_factory(request)

    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(
            handler,
            messages=({"role": "user", "content": "private-prompt-sentinel"},),
        )

    assert captured.value.category is category
    assert captured.value.timeout_kind is timeout_kind
    assert attempts == 1
    chain = _exception_chain_text(captured.value)
    assert "secret" not in chain
    assert "private-prompt-sentinel" not in chain


def test_total_deadline_expiry_is_enforced_and_sanitized() -> None:
    ticks = iter((0.0, 0.0, 0.0, 0.0, 2.0))
    client = OllamaLocalClient(
        total_timeout_seconds=1.0,
        transport=httpx.MockTransport(
            lambda _request: _chat_response({"answer": "raw-response-sentinel"})
        ),
        monotonic=lambda: next(ticks),
    )

    with pytest.raises(OllamaLocalRequestError) as captured:
        client.complete_validated_json(
            messages=({"role": "user", "content": "private-prompt-sentinel"},),
            schema=SCHEMA,
            validator=lambda payload, _model: payload,
        )

    assert captured.value.category is ProviderFailureCategory.TIMEOUT
    assert captured.value.timeout_kind is OllamaLocalTimeoutKind.TOTAL
    chain = _exception_chain_text(captured.value)
    assert "raw-response-sentinel" not in chain
    assert "private-prompt-sentinel" not in chain


def test_total_deadline_rejects_over_deadline_application_validation() -> None:
    clock = {"now": 0.0}

    def validate(payload: dict[str, Any], _model: str) -> dict[str, Any]:
        clock["now"] = 2.0
        return payload

    client = OllamaLocalClient(
        total_timeout_seconds=1.0,
        transport=httpx.MockTransport(
            lambda _request: _chat_response({"answer": "ok"})
        ),
        monotonic=lambda: clock["now"],
    )

    with pytest.raises(OllamaLocalRequestError) as captured:
        client.complete_validated_json(
            messages=({"role": "user", "content": "hello"},),
            schema=SCHEMA,
            validator=validate,
        )

    assert captured.value.category is ProviderFailureCategory.TIMEOUT


def test_response_is_bounded_and_does_not_expose_content() -> None:
    sentinel = "raw-response-sentinel"
    oversized = sentinel.encode() + b"x" * MAX_PROVIDER_RESPONSE_BYTES

    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(lambda _request: httpx.Response(200, content=oversized))

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert sentinel not in _exception_chain_text(captured.value)


def test_request_is_bounded_before_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return _chat_response({"answer": "ok"})

    monkeypatch.setattr(ollama_http, "MAX_OLLAMA_REQUEST_BYTES", 128)
    with pytest.raises(OllamaLocalConfigurationError, match="size limit") as captured:
        _complete(
            handler,
            messages=({"role": "user", "content": "request-sentinel" * 20},),
        )

    assert attempts == 0
    assert "request-sentinel" not in str(captured.value)
    assert MAX_OLLAMA_REQUEST_BYTES == 48 * 1024 * 1024


def test_http_failure_does_not_expose_provider_body_or_prompt() -> None:
    with pytest.raises(OllamaLocalRequestError) as captured:
        _complete(
            lambda _request: httpx.Response(400, text="raw-response-sentinel"),
            messages=({"role": "user", "content": "private-prompt-sentinel"},),
        )

    assert captured.value.category is ProviderFailureCategory.REQUEST_REJECTED
    assert captured.value.http_status == 400
    chain = _exception_chain_text(captured.value)
    assert "raw-response-sentinel" not in chain
    assert "private-prompt-sentinel" not in chain
