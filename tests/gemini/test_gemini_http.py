from __future__ import annotations

from collections.abc import Callable, Iterator

import httpx
import pytest

from ai_vastu.gemini_http import post_json_with_retry
from ai_vastu.provider_runtime import (
    MAX_PROVIDER_RESPONSE_BYTES,
    ProviderBudget,
    ProviderFailureCategory,
    ProviderRuntimeError,
)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class _OversizedChunkStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b"x" * MAX_PROVIDER_RESPONSE_BYTES
        yield b"x"


class _LateChunkStream(httpx.SyncByteStream):
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def __iter__(self) -> Iterator[bytes]:
        self._clock.now = 6.0
        yield b'{"ok":true}'


class _MislabeledDeflateStream(httpx.SyncByteStream):
    def __iter__(self) -> Iterator[bytes]:
        yield b'{"not-really-deflate":true}'


@pytest.fixture(autouse=True)
def _clear_gemini_budget_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for suffix in (
        "ATTEMPT_TIMEOUT_SECONDS",
        "TOTAL_TIMEOUT_SECONDS",
        "RETRY_DELAY_SECONDS",
        "MAX_RETRY_AFTER_SECONDS",
    ):
        monkeypatch.delenv(f"AI_VASTU_GEMINI_{suffix}", raising=False)


def _call(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    clock: Clock | None = None,
    budget: ProviderBudget | None = None,
    max_attempts: int = 2,
) -> httpx.Response:
    active_clock = clock or Clock()
    with httpx.Client(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        transport=httpx.MockTransport(handler),
    ) as client:
        return post_json_with_retry(
            client,
            "/models/gemini-pinned:generateContent",
            json_payload={"private": "prompt"},
            max_attempts=max_attempts,
            budget=budget,
            monotonic=active_clock.monotonic,
            sleeper=active_clock.sleep,
        )


def test_success_is_returned_without_retry_or_sleep() -> None:
    clock = Clock()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True})

    response = _call(handler, clock=clock)

    assert response.json() == {"ok": True}
    assert calls == 1
    assert clock.sleeps == []


def test_request_requires_identity_content_encoding() -> None:
    observed_accept_encoding: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed_accept_encoding.append(request.headers["Accept-Encoding"])
        return httpx.Response(200, json={"ok": True})

    response = _call(handler)

    assert response.json() == {"ok": True}
    assert observed_accept_encoding == ["identity"]


def test_decode_failure_is_invalid_response_without_retry() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            headers={"Content-Encoding": "deflate"},
            stream=_MislabeledDeflateStream(),
        )

    with pytest.raises(ProviderRuntimeError) as captured:
        _call(handler)

    assert calls == 1
    assert captured.value.category is ProviderFailureCategory.INVALID_RESPONSE


def test_default_helper_budget_is_loaded_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS", "4")
    monkeypatch.setenv("AI_VASTU_GEMINI_RETRY_DELAY_SECONDS", "0")
    monkeypatch.setenv("AI_VASTU_GEMINI_MAX_RETRY_AFTER_SECONDS", "0")
    timeouts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeout = request.extensions["timeout"]
        assert isinstance(timeout, dict)
        timeouts.append(float(timeout["read"]))
        return httpx.Response(200, json={"ok": True})

    response = _call(handler)

    assert response.status_code == 200
    assert timeouts == [2.0]


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
def test_client_and_auth_statuses_fail_without_retry(
    status_code: int,
    category: ProviderFailureCategory,
) -> None:
    clock = Clock()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, text="raw secret response")

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(handler, clock=clock)

    assert calls == 1
    assert clock.sleeps == []
    assert raised.value.category is category
    assert str(raised.value) == f"gemini request failed ({category.value})."
    assert "raw secret response" not in str(raised.value)


@pytest.mark.parametrize("status_code", (408, 429, 500, 502, 503, 504))
def test_transient_status_retries_once_with_same_pinned_url(status_code: int) -> None:
    clock = Clock()
    urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        urls.append(str(request.url))
        if len(urls) == 1:
            return httpx.Response(status_code, json={"error": "transient"})
        return httpx.Response(200, json={"ok": True})

    response = _call(handler, clock=clock)

    assert response.json() == {"ok": True}
    assert len(urls) == 2
    assert urls[0] == urls[1]
    assert urls[0].endswith("/models/gemini-pinned:generateContent")
    assert clock.sleeps == [1.0]


@pytest.mark.parametrize(
    ("status_code", "category"),
    (
        (408, ProviderFailureCategory.TIMEOUT),
        (429, ProviderFailureCategory.RATE_LIMITED),
        (500, ProviderFailureCategory.UNAVAILABLE),
        (504, ProviderFailureCategory.TIMEOUT),
    ),
)
def test_second_transient_failure_is_typed(
    status_code: int,
    category: ProviderFailureCategory,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, text="do not leak")

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(handler)

    assert calls == 2
    assert raised.value.category is category
    assert "do not leak" not in str(raised.value)


@pytest.mark.parametrize(
    ("failure_type", "category"),
    (
        (httpx.ConnectError, ProviderFailureCategory.UNAVAILABLE),
        (httpx.ReadError, ProviderFailureCategory.UNAVAILABLE),
        (httpx.ReadTimeout, ProviderFailureCategory.TIMEOUT),
        (httpx.ConnectTimeout, ProviderFailureCategory.TIMEOUT),
    ),
)
def test_transport_failure_retries_once_and_is_sanitized_when_exhausted(
    failure_type: type[httpx.TransportError],
    category: ProviderFailureCategory,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise failure_type("secret-key and prompt", request=request)

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(handler)

    assert calls == 2
    assert raised.value.category is category
    assert "secret-key" not in str(raised.value)
    assert "prompt" not in str(raised.value)


def test_ineligible_local_protocol_failure_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.LocalProtocolError("local defect", request=request)

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(handler)

    assert calls == 1
    assert raised.value.category is ProviderFailureCategory.UNAVAILABLE


@pytest.mark.parametrize(
    "response",
    (
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json=["not", "an", "object"]),
    ),
)
def test_malformed_success_is_not_retried(response: httpx.Response) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(handler)

    assert calls == 1
    assert raised.value.category is ProviderFailureCategory.INVALID_RESPONSE


@pytest.mark.parametrize(
    ("retry_after", "expected_delay"),
    (("4", 4.0), ("99", 5.0), ("invalid", 1.0), ("-2", 1.0)),
)
def test_retry_after_is_deterministic_and_capped(
    retry_after: str,
    expected_delay: float,
) -> None:
    clock = Clock()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": retry_after},
                json={"error": "rate limited"},
            )
        return httpx.Response(200, json={"ok": True})

    response = _call(handler, clock=clock)

    assert response.status_code == 200
    assert clock.sleeps == [expected_delay]


def test_remaining_budget_is_checked_before_sleep() -> None:
    clock = Clock()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            429,
            headers={"Retry-After": "5"},
            json={"error": "rate limited"},
        )

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(
            handler,
            clock=clock,
            budget=ProviderBudget(
                attempt_timeout_seconds=3.0,
                total_timeout_seconds=3.0,
                retry_delay_seconds=1.0,
                max_retry_after_seconds=5.0,
            ),
        )

    assert calls == 1
    assert clock.sleeps == []
    assert raised.value.category is ProviderFailureCategory.TIMEOUT


def test_attempt_timeout_is_capped_by_remaining_total_budget() -> None:
    clock = Clock()
    timeouts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeout = request.extensions["timeout"]
        assert isinstance(timeout, dict)
        timeouts.append(float(timeout["read"]))
        if len(timeouts) == 1:
            clock.now = 3.0
            return httpx.Response(503, json={"error": "retry"})
        return httpx.Response(200, json={"ok": True})

    response = _call(
        handler,
        clock=clock,
        budget=ProviderBudget(
            attempt_timeout_seconds=4.0,
            total_timeout_seconds=5.0,
            retry_delay_seconds=0.0,
            max_retry_after_seconds=0.0,
        ),
    )

    assert response.status_code == 200
    assert timeouts == [4.0, 2.0]


@pytest.mark.parametrize("max_attempts", (0, 3, True))
def test_attempt_count_cannot_exceed_code_owned_limit(max_attempts: int) -> None:
    with pytest.raises(ValueError, match="one or two"):
        _call(
            lambda _request: httpx.Response(200, json={"ok": True}),
            max_attempts=max_attempts,
        )


@pytest.mark.parametrize("declared", (True, False))
def test_oversized_success_response_is_rejected_without_retry(declared: bool) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if declared:
            return httpx.Response(
                200,
                headers={"Content-Length": str(MAX_PROVIDER_RESPONSE_BYTES + 1)},
                content=b"{}",
            )
        return httpx.Response(200, stream=_OversizedChunkStream())

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(handler)

    assert calls == 1
    assert raised.value.category is ProviderFailureCategory.INVALID_RESPONSE


def test_total_deadline_is_enforced_while_streaming_response() -> None:
    clock = Clock()

    with pytest.raises(ProviderRuntimeError) as raised:
        _call(
            lambda _request: httpx.Response(200, stream=_LateChunkStream(clock)),
            clock=clock,
            budget=ProviderBudget(
                attempt_timeout_seconds=4.0,
                total_timeout_seconds=5.0,
                retry_delay_seconds=0.0,
                max_retry_after_seconds=0.0,
            ),
        )

    assert raised.value.category is ProviderFailureCategory.TIMEOUT
