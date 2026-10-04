from __future__ import annotations

import math
from collections.abc import Iterator

import httpx
import pytest

from ai_vastu.provider_runtime import (
    ProviderBudget,
    ProviderBudgetConfigurationError,
    ProviderFailureCategory,
    ProviderRuntimeError,
    load_provider_budget,
    read_limited_provider_response,
)


class _MislabeledDeflateStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b'{"not-really-deflate":true}'


def test_failure_categories_are_stable_wire_values() -> None:
    assert tuple(category.value for category in ProviderFailureCategory) == (
        "authentication",
        "request_rejected",
        "rate_limited",
        "unavailable",
        "timeout",
        "invalid_response",
    )


def test_runtime_error_exposes_only_typed_sanitized_context() -> None:
    error = ProviderRuntimeError(
        ProviderFailureCategory.AUTHENTICATION,
        "openrouter\nBearer secret-key",
    )

    assert error.category is ProviderFailureCategory.AUTHENTICATION
    assert error.provider == "provider"
    assert str(error) == "provider request failed (authentication)."
    assert "secret-key" not in str(error)


def test_response_content_decoding_failure_is_sanitized() -> None:
    request = httpx.Request("GET", "https://provider.example/response")
    response = httpx.Response(
        200,
        headers={"Content-Encoding": "deflate"},
        stream=_MislabeledDeflateStream(),
        request=request,
    )

    with pytest.raises(ProviderRuntimeError) as captured:
        read_limited_provider_response(response, provider="gemini")

    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE
    assert str(captured.value) == "gemini request failed (invalid_response)."
    assert "not-really-deflate" not in str(captured.value)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("attempt_timeout_seconds", 0.0),
        ("attempt_timeout_seconds", -1.0),
        ("attempt_timeout_seconds", math.inf),
        ("total_timeout_seconds", 0.0),
        ("total_timeout_seconds", math.nan),
        ("retry_delay_seconds", -0.1),
        ("retry_delay_seconds", math.inf),
        ("max_retry_after_seconds", -0.1),
    ),
)
def test_budget_rejects_unbounded_or_negative_values(field: str, value: float) -> None:
    values = {
        "attempt_timeout_seconds": 2.0,
        "total_timeout_seconds": 5.0,
        "retry_delay_seconds": 0.5,
        "max_retry_after_seconds": 2.0,
    }
    values[field] = value

    with pytest.raises(ProviderBudgetConfigurationError):
        ProviderBudget(**values)


def test_budget_rejects_total_shorter_than_one_attempt() -> None:
    with pytest.raises(
        ProviderBudgetConfigurationError,
        match="total_timeout_seconds must be at least attempt_timeout_seconds",
    ):
        ProviderBudget(
            attempt_timeout_seconds=3.0,
            total_timeout_seconds=2.0,
        )


def test_budget_loader_uses_defaults_and_explicit_overrides() -> None:
    default = ProviderBudget(
        attempt_timeout_seconds=3.0,
        total_timeout_seconds=8.0,
        retry_delay_seconds=1.0,
        max_retry_after_seconds=4.0,
    )

    loaded = load_provider_budget(
        {
            "AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS": " 2.5 ",
            "AI_VASTU_GEMINI_RETRY_DELAY_SECONDS": "0",
        },
        prefix="AI_VASTU_GEMINI",
        default=default,
    )

    assert loaded == ProviderBudget(
        attempt_timeout_seconds=2.5,
        total_timeout_seconds=8.0,
        retry_delay_seconds=0.0,
        max_retry_after_seconds=4.0,
    )


@pytest.mark.parametrize(
    ("environment", "prefix", "expected"),
    (
        (
            {"AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS": "abc"},
            "AI_VASTU_GEMINI",
            "AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS must be a number",
        ),
        ({}, "invalid-prefix", "prefix must contain uppercase"),
    ),
)
def test_budget_loader_rejects_invalid_configuration(
    environment: dict[str, str],
    prefix: str,
    expected: str,
) -> None:
    with pytest.raises(ProviderBudgetConfigurationError, match=expected):
        load_provider_budget(
            environment,
            prefix=prefix,
            default=ProviderBudget(1.0, 2.0),
        )
