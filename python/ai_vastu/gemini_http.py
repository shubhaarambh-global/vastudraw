from __future__ import annotations

import json
import math
import os
import time
from collections.abc import Callable
from typing import Any

import httpx

from ai_vastu.provider_runtime import (
    DEFAULT_GEMINI_BUDGET,
    ProviderBudget,
    ProviderFailureCategory,
    ProviderRuntimeError,
    load_provider_budget,
    read_limited_provider_response,
)

_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 2


def _status_category(status_code: int) -> ProviderFailureCategory:
    if status_code in {401, 403}:
        return ProviderFailureCategory.AUTHENTICATION
    if status_code in {408, 504}:
        return ProviderFailureCategory.TIMEOUT
    if status_code == 429:
        return ProviderFailureCategory.RATE_LIMITED
    if 400 <= status_code < 500:
        return ProviderFailureCategory.REQUEST_REJECTED
    return ProviderFailureCategory.UNAVAILABLE


def _transport_category(exc: httpx.TransportError) -> ProviderFailureCategory:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderFailureCategory.TIMEOUT
    return ProviderFailureCategory.UNAVAILABLE


def _eligible_transport_failure(exc: httpx.TransportError) -> bool:
    return isinstance(
        exc,
        (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
            httpx.ProxyError,
        ),
    )


def _retry_delay(response: httpx.Response | None, budget: ProviderBudget) -> float:
    delay = budget.retry_delay_seconds
    if response is None:
        return delay
    raw_retry_after = response.headers.get("Retry-After")
    if raw_retry_after is None:
        return delay
    try:
        retry_after = float(raw_retry_after.strip())
    except ValueError:
        return delay
    if not math.isfinite(retry_after) or retry_after < 0:
        return delay
    return max(delay, min(retry_after, budget.max_retry_after_seconds))


def post_json_with_retry(
    client: httpx.Client,
    url: str,
    *,
    json_payload: dict[str, Any],
    max_attempts: int = _MAX_ATTEMPTS,
    base_delay_seconds: float = 1.0,
    budget: ProviderBudget | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """POST Gemini JSON under one deadline and at most one deterministic retry."""

    if isinstance(max_attempts, bool) or not 1 <= max_attempts <= _MAX_ATTEMPTS:
        raise ValueError("Gemini max_attempts must be one or two.")
    default_budget = ProviderBudget(
        attempt_timeout_seconds=DEFAULT_GEMINI_BUDGET.attempt_timeout_seconds,
        total_timeout_seconds=DEFAULT_GEMINI_BUDGET.total_timeout_seconds,
        retry_delay_seconds=base_delay_seconds,
        max_retry_after_seconds=DEFAULT_GEMINI_BUDGET.max_retry_after_seconds,
    )
    active_budget = budget or load_provider_budget(
        os.environ,
        prefix="AI_VASTU_GEMINI",
        default=default_budget,
    )
    deadline = monotonic() + active_budget.total_timeout_seconds
    last_category = ProviderFailureCategory.UNAVAILABLE

    for attempt in range(max_attempts):
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ProviderRuntimeError(
                ProviderFailureCategory.TIMEOUT,
                "gemini",
            )

        response: httpx.Response | None = None
        retryable = False
        try:
            with client.stream(
                "POST",
                url,
                json=json_payload,
                headers={"Accept-Encoding": "identity"},
                timeout=min(active_budget.attempt_timeout_seconds, remaining),
            ) as streamed_response:
                response = streamed_response
                if monotonic() >= deadline:
                    raise ProviderRuntimeError(
                        ProviderFailureCategory.TIMEOUT,
                        "gemini",
                    )
                if response.is_success:
                    response_bytes = read_limited_provider_response(
                        response,
                        provider="gemini",
                        deadline=deadline,
                        monotonic=monotonic,
                    )
                    try:
                        payload = json.loads(response_bytes)
                    except (ValueError, UnicodeDecodeError):
                        raise ProviderRuntimeError(
                            ProviderFailureCategory.INVALID_RESPONSE,
                            "gemini",
                        ) from None
                    if not isinstance(payload, dict):
                        raise ProviderRuntimeError(
                            ProviderFailureCategory.INVALID_RESPONSE,
                            "gemini",
                        )
                    return httpx.Response(
                        status_code=response.status_code,
                        headers=response.headers,
                        content=response_bytes,
                        request=response.request,
                    )

                last_category = _status_category(response.status_code)
                retryable = response.status_code in _TRANSIENT_STATUS
        except httpx.TransportError as exc:
            last_category = _transport_category(exc)
            retryable = _eligible_transport_failure(exc)

        if not retryable or attempt + 1 >= max_attempts:
            raise ProviderRuntimeError(last_category, "gemini") from None

        delay = _retry_delay(response, active_budget)
        remaining = deadline - monotonic()
        if remaining <= 0 or delay >= remaining:
            raise ProviderRuntimeError(
                ProviderFailureCategory.TIMEOUT,
                "gemini",
            )
        if delay:
            sleeper(delay)

    raise ProviderRuntimeError(last_category, "gemini")
