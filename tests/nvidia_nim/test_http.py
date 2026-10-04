from __future__ import annotations

import json

import httpx
import pytest

from ai_vastu.nvidia_nim_http import (
    INACTIVE_UNQUALIFIED_TEXT_MODEL,
    NVIDIA_NIM_API_BASE,
    PRIMARY_TEXT_MODEL,
    NvidiaNimClient,
    NvidiaNimConfigurationError,
    NvidiaNimFailureStage,
    NvidiaNimModelPolicy,
    NvidiaNimRequestError,
)
from ai_vastu.provider_runtime import ProviderFailureCategory


def _completion(value: dict[str, object]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "model": PRIMARY_TEXT_MODEL,
            "choices": [{"message": {"content": json.dumps(value)}}],
        },
    )


def test_environment_requires_only_nvidia_key_and_pinned_base_url() -> None:
    client = NvidiaNimClient.from_environment(
        {
            "NVIDIA_API_KEY": "secret",
            "AI_VASTU_NVIDIA_BASE_URL": NVIDIA_NIM_API_BASE,
        }
    )
    assert isinstance(client, NvidiaNimClient)

    with pytest.raises(NvidiaNimConfigurationError):
        NvidiaNimClient.from_environment({"NVIDIA_API_KEY": ""})
    with pytest.raises(NvidiaNimConfigurationError):
        NvidiaNimClient.from_environment(
            {
                "NVIDIA_API_KEY": "secret",
                "AI_VASTU_NVIDIA_BASE_URL": "https://example.invalid/v1",
            }
        )


def test_active_policy_is_ultra_only_and_rejects_legacy_fallback() -> None:
    policy = NvidiaNimModelPolicy()

    assert policy.text_chain == (PRIMARY_TEXT_MODEL,)
    assert PRIMARY_TEXT_MODEL == "nvidia/nemotron-3-ultra-550b-a55b"
    assert INACTIVE_UNQUALIFIED_TEXT_MODEL == (
        "nvidia/nemotron-3.5-lightning-30b-a3b"
    )
    with pytest.raises(NvidiaNimConfigurationError, match="inactive"):
        NvidiaNimModelPolicy.from_environment(
            {"AI_VASTU_NVIDIA_FALLBACK_MODEL": INACTIVE_UNQUALIFIED_TEXT_MODEL}
        )


def test_unavailable_retries_same_model_once() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content)["model"])
        if len(seen) == 1:
            return httpx.Response(503)
        return _completion({"answer": "ok"})

    result = NvidiaNimClient(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return json"},),
        models=NvidiaNimModelPolicy().text_chain,
        validator=lambda payload, model: (payload, model),
        temperature=0,
        response_format={"type": "json_object"},
    )

    assert result == ({"answer": "ok"}, PRIMARY_TEXT_MODEL)
    assert seen == [PRIMARY_TEXT_MODEL, PRIMARY_TEXT_MODEL]


@pytest.mark.parametrize(
    ("status", "category"),
    [
        (401, ProviderFailureCategory.AUTHENTICATION),
        (403, ProviderFailureCategory.AUTHENTICATION),
        (400, ProviderFailureCategory.REQUEST_REJECTED),
        (422, ProviderFailureCategory.REQUEST_REJECTED),
        (429, ProviderFailureCategory.RATE_LIMITED),
    ],
)
def test_auth_rejection_and_rate_limit_are_never_retried(
    status: int,
    category: ProviderFailureCategory,
) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(status, text="provider raw secret")

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="credential-secret",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "private prompt"},),
            models=NvidiaNimModelPolicy().text_chain,
            validator=lambda payload, _model: payload,
            temperature=0,
        )

    assert captured.value.category is category
    assert captured.value.http_status == status
    assert captured.value.attempts == 1
    assert attempts == 1
    assert "credential-secret" not in str(captured.value)
    assert "private prompt" not in str(captured.value)
    assert "provider raw secret" not in str(captured.value)


def test_malformed_application_output_is_not_retried() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return _completion({"answer": "wrong"})

    def reject(_payload: dict[str, object], _model: str) -> object:
        raise ValueError("raw invalid output")

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="secret",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "return json"},),
            models=NvidiaNimModelPolicy().text_chain,
            validator=reject,
            temperature=0,
        )

    assert attempts == 1
    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert captured.value.stage is NvidiaNimFailureStage.APPLICATION_VALIDATION
    assert "raw invalid output" not in str(captured.value)


def test_ultra_request_omits_unsupported_response_format() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _completion({"ok": True})

    NvidiaNimClient(
        api_key="secret",
        transport=httpx.MockTransport(handler),
    ).complete_validated_json(
        messages=({"role": "user", "content": "return json"},),
        models=(PRIMARY_TEXT_MODEL,),
        validator=lambda payload, _model: payload,
        temperature=0,
        response_format={"type": "json_object"},
    )

    assert "response_format" not in bodies[0]


@pytest.mark.parametrize(
    "response",
    (
        httpx.Response(200, content=b"not-json"),
        httpx.Response(
            200,
            json={
                "model": PRIMARY_TEXT_MODEL,
                "choices": [{"message": {"content": "```json\n{}\n```"}}],
            },
        ),
    ),
)
def test_strict_json_failures_are_never_retried(response: httpx.Response) -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return response

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="secret",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "private"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0,
        )

    assert attempts == 1
    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert captured.value.stage is NvidiaNimFailureStage.STRICT_JSON


def test_provenance_failure_is_never_retried() -> None:
    attempts = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            200,
            json={
                "model": "nvidia/unrequested-model",
                "choices": [{"message": {"content": '{"ok":true}'}}],
            },
        )

    with pytest.raises(NvidiaNimRequestError) as captured:
        NvidiaNimClient(
            api_key="secret",
            transport=httpx.MockTransport(handler),
        ).complete_validated_json(
            messages=({"role": "user", "content": "private"},),
            models=(PRIMARY_TEXT_MODEL,),
            validator=lambda payload, _model: payload,
            temperature=0,
        )

    assert attempts == 1
    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert captured.value.stage is NvidiaNimFailureStage.PROVENANCE
