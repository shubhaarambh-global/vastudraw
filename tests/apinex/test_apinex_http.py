from __future__ import annotations

import base64
import inspect
import json
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, ConfigDict, StrictBool, ValidationError

from ai_vastu.apinex_http import (
    APINEX_API_BASE,
    APINEX_MODEL,
    DEFAULT_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_POOL_TIMEOUT_SECONDS,
    DEFAULT_READ_TIMEOUT_SECONDS,
    DEFAULT_TOTAL_TIMEOUT_SECONDS,
    DEFAULT_WRITE_TIMEOUT_SECONDS,
    MAX_APINEX_REQUEST_BYTES,
    MAX_CONNECT_TIMEOUT_SECONDS,
    MAX_POOL_TIMEOUT_SECONDS,
    MAX_READ_TIMEOUT_SECONDS,
    MAX_TOTAL_TIMEOUT_SECONDS,
    MAX_WRITE_TIMEOUT_SECONDS,
    ApinexClient,
    ApinexConfigurationError,
    ApinexFailureStage,
    ApinexRequestError,
)
from ai_vastu.provider_runtime import ProviderFailureCategory


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: StrictBool


def _completion(content: str = '{"ok":true}', model: str = APINEX_MODEL) -> dict[str, Any]:
    return {
        "id": "synthetic",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": content}}],
    }


def _client(handler: Any, **kwargs: Any) -> ApinexClient:
    return ApinexClient(
        api_key="test-key-never-logged",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def _call(client: ApinexClient) -> Contract:
    return client.complete_validated_json(
        messages=(
            {"role": "system", "content": "Synthetic contract."},
            {"role": "user", "content": "Return the synthetic result."},
        ),
        schema=Contract.model_json_schema(),
        validator=lambda payload, _model: Contract.model_validate(payload),
    )


def test_pinned_defaults_and_environment_policy() -> None:
    assert APINEX_API_BASE == "https://api.apinex.bond/v1"
    assert APINEX_MODEL == "free/gpt-6-luna"
    assert (
        DEFAULT_CONNECT_TIMEOUT_SECONDS,
        DEFAULT_READ_TIMEOUT_SECONDS,
        DEFAULT_TOTAL_TIMEOUT_SECONDS,
        DEFAULT_WRITE_TIMEOUT_SECONDS,
        DEFAULT_POOL_TIMEOUT_SECONDS,
    ) == (5.0, 180.0, 240.0, 30.0, 5.0)
    client = ApinexClient.from_environment(
        {"APP_ENV": "development", "APINEX_API_KEY": "synthetic"}
    )
    assert isinstance(client, ApinexClient)


@pytest.mark.parametrize(
    ("field", "maximum"),
    (
        ("connect_timeout_seconds", MAX_CONNECT_TIMEOUT_SECONDS),
        ("read_timeout_seconds", MAX_READ_TIMEOUT_SECONDS),
        ("total_timeout_seconds", MAX_TOTAL_TIMEOUT_SECONDS),
        ("write_timeout_seconds", MAX_WRITE_TIMEOUT_SECONDS),
        ("pool_timeout_seconds", MAX_POOL_TIMEOUT_SECONDS),
    ),
)
def test_timeout_maxima_are_enforced(field: str, maximum: float) -> None:
    with pytest.raises(ApinexConfigurationError):
        ApinexClient(api_key="synthetic", **{field: maximum + 0.001})


def test_transport_disables_redirects_and_environment_proxies() -> None:
    source = inspect.getsource(ApinexClient._send)
    assert "trust_env=False" in source
    assert "follow_redirects=False" in source


@pytest.mark.parametrize(
    ("base_url", "model"),
    (
        ("http://api.apinex.bond/v1", APINEX_MODEL),
        ("https://example.com/v1", APINEX_MODEL),
        (APINEX_API_BASE, "gpt-6-luna"),
        (APINEX_API_BASE, "free/gpt-6-astra"),
    ),
)
def test_endpoint_and_exact_model_are_pinned(base_url: str, model: str) -> None:
    with pytest.raises(ApinexConfigurationError):
        ApinexClient(api_key="synthetic", base_url=base_url, model=model)


@pytest.mark.parametrize("app_env", ("", "staging", "production"))
def test_only_explicit_development_environment_is_allowed(app_env: str) -> None:
    with pytest.raises(ApinexConfigurationError):
        ApinexClient.from_environment({"APP_ENV": app_env, "APINEX_API_KEY": "synthetic"})


def test_fallback_and_missing_key_are_rejected() -> None:
    with pytest.raises(ApinexConfigurationError):
        ApinexClient.from_environment({"APP_ENV": "development"})
    with pytest.raises(ApinexConfigurationError):
        ApinexClient.from_environment(
            {
                "APP_ENV": "development",
                "APINEX_API_KEY": "synthetic",
                "AI_VASTU_APINEX_FALLBACK_MODEL": APINEX_MODEL,
            }
        )


def test_structured_request_is_strict_zero_temperature_non_streaming_one_attempt() -> None:
    calls: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        assert request.url == "https://api.apinex.bond/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key-never-logged"
        return httpx.Response(200, json=_completion())

    result = _call(_client(handler))

    assert result.ok is True
    assert len(calls) == 1
    body = calls[0]
    assert body["model"] == APINEX_MODEL
    assert body["stream"] is False
    assert body["temperature"] == 0
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"] == Contract.model_json_schema()
    system = body["messages"][0]["content"]
    assert "raw JSON only" in system
    assert "extra keys" in system


@pytest.mark.parametrize(
    ("content_type", "data"),
    (
        ("image/png", b"\x89PNG\r\n\x1a\nsynthetic"),
        ("image/jpeg", b"\xff\xd8\xffsynthetic"),
    ),
)
def test_validated_png_and_jpeg_become_matching_data_urls(
    content_type: str, data: bytes
) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=_completion())

    encoded = base64.b64encode(data).decode("ascii")
    _client(handler).complete_validated_json(
        messages=(
            {"role": "system", "content": "Synthetic."},
            {"role": "user", "content": "Inspect.", "images": [encoded]},
        ),
        schema=Contract.model_json_schema(),
        validator=lambda payload, _model: Contract.model_validate(payload),
    )
    part = seen[0]["messages"][1]["content"][1]
    assert part["type"] == "image_url"
    assert part["image_url"]["url"] == f"data:{content_type};base64,{encoded}"


@pytest.mark.parametrize(
    "content",
    (
        '```json\n{"ok":true}\n```',
        'Result: {"ok":true}',
        '{"ok":true,"extra":1}',
        '{"ok":"yes"}',
    ),
)
def test_fenced_prose_and_wrong_schema_outputs_fail_closed(content: str) -> None:
    client = _client(lambda _request: httpx.Response(200, json=_completion(content)))
    with pytest.raises(ApinexRequestError) as captured:
        _call(client)
    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert captured.value.stage in {
        ApinexFailureStage.STRICT_JSON,
        ApinexFailureStage.APPLICATION_VALIDATION,
    }


def test_returned_model_mismatch_and_malformed_envelope_fail_closed() -> None:
    mismatch = _client(lambda _request: httpx.Response(200, json=_completion(model="gpt-6-luna")))
    with pytest.raises(ApinexRequestError) as captured:
        _call(mismatch)
    assert captured.value.stage is ApinexFailureStage.PROVENANCE

    malformed = _client(lambda _request: httpx.Response(200, json={"model": APINEX_MODEL}))
    with pytest.raises(ApinexRequestError) as captured:
        _call(malformed)
    assert captured.value.stage is ApinexFailureStage.STRICT_JSON


@pytest.mark.parametrize(
    ("status", "category"),
    (
        (401, ProviderFailureCategory.AUTHENTICATION),
        (429, ProviderFailureCategory.RATE_LIMITED),
        (400, ProviderFailureCategory.REQUEST_REJECTED),
        (503, ProviderFailureCategory.UNAVAILABLE),
    ),
)
def test_http_failures_are_sanitized(status: int, category: ProviderFailureCategory) -> None:
    secret = "provider-body-secret"
    client = _client(lambda _request: httpx.Response(status, text=f"failure {secret}"))
    with pytest.raises(ApinexRequestError) as captured:
        _call(client)
    assert captured.value.category is category
    assert secret not in str(captured.value)
    assert "test-key-never-logged" not in str(captured.value)


def test_timeout_and_unavailable_are_single_attempt_and_sanitized() -> None:
    for exception, category in (
        (httpx.ReadTimeout("secret timeout"), ProviderFailureCategory.TIMEOUT),
        (httpx.ConnectError("secret unavailable"), ProviderFailureCategory.UNAVAILABLE),
    ):
        calls = 0

        failure = exception

        def handler(
            _request: httpx.Request,
            failure: httpx.TransportError = failure,
        ) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise failure

        with pytest.raises(ApinexRequestError) as captured:
            _call(_client(handler))
        assert calls == 1
        assert captured.value.category is category
        assert "secret" not in str(captured.value)


def test_redirect_is_not_followed() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(302, headers={"Location": "https://example.com/steal"})

    with pytest.raises(ApinexRequestError) as captured:
        _call(_client(handler))
    assert calls == 1
    assert captured.value.category is ProviderFailureCategory.UNAVAILABLE


def test_model_inventory_requires_exact_pin() -> None:
    good = _client(lambda _request: httpx.Response(200, json={"data": [{"id": APINEX_MODEL}]}))
    assert good.verify_pinned_model_available() == APINEX_MODEL
    bad = _client(lambda _request: httpx.Response(200, json={"data": [{"id": "gpt-6-luna"}]}))
    with pytest.raises(ApinexRequestError) as captured:
        bad.verify_pinned_model_available()
    assert captured.value.stage is ApinexFailureStage.MODEL_INVENTORY

    malformed = _client(
        lambda _request: httpx.Response(
            200, json={"data": [{"id": APINEX_MODEL}, {"unexpected": True}]}
        )
    )
    with pytest.raises(ApinexRequestError):
        malformed.verify_pinned_model_available()


def test_user_only_structured_call_gets_raw_json_instruction() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=_completion())

    _client(handler).complete_validated_json(
        messages=({"role": "user", "content": "Synthetic."},),
        schema=Contract.model_json_schema(),
        validator=lambda payload, _model: Contract.model_validate(payload),
    )
    assert seen[0]["messages"][0] == {
        "role": "system",
        "content": (
            "Return raw JSON only. Match the supplied schema exactly. Do not use "
            "Markdown or code fences. Do not include prose outside JSON. Do not add "
            "extra keys."
        ),
    }


def test_response_and_request_size_are_bounded() -> None:
    oversized_response = b"x" * (2 * 1024 * 1024 + 1)
    client = _client(lambda _request: httpx.Response(200, content=oversized_response))
    with pytest.raises(ApinexRequestError) as captured:
        _call(client)
    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE

    huge = "x" * MAX_APINEX_REQUEST_BYTES
    with pytest.raises(ApinexConfigurationError):
        _client(lambda _request: httpx.Response(200, json=_completion())).complete_validated_json(
            messages=({"role": "user", "content": huge},),
            schema=Contract.model_json_schema(),
            validator=lambda payload, _model: Contract.model_validate(payload),
        )


def test_validation_error_cannot_leak_input() -> None:
    secret = "sensitive-model-output"
    client = _client(
        lambda _request: httpx.Response(200, json=_completion(json.dumps({"ok": secret})))
    )
    with pytest.raises(ApinexRequestError) as captured:
        _call(client)
    assert captured.value.stage is ApinexFailureStage.APPLICATION_VALIDATION
    assert secret not in str(captured.value)
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_contract_itself_rejects_extra_keys() -> None:
    with pytest.raises(ValidationError):
        Contract.model_validate({"ok": True, "extra": 1})
