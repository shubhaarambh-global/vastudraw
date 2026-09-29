from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest

from ai_vastu.billing.phonepe import (
    MAX_PHONEPE_RESPONSE_BYTES,
    PhonePeClient,
    PhonePeFailureCategory,
    PhonePeOrderState,
    PhonePeProviderError,
    PhonePeRequestError,
    validate_callback_authorization,
)

NOW = 1_700_000_000.0
MERCHANT_ORDER_ID = "order_stored_123"
PROVIDER_ORDER_ID = "OMO123456789"
CHECKOUT_URL = "https://mercury-uat.phonepe.com/transact/uat_v2?token=test-token"


def _token_response(
    *, token: str = "oauth-token", expires_at: float = NOW + 3600
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "access_token": token,
            "token_type": "O-Bearer",
            "issued_at": int(NOW),
            "expires_at": int(expires_at),
        },
    )


def _checkout_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "orderId": PROVIDER_ORDER_ID,
            "state": "PENDING",
            "expireAt": 1_700_001_200_000,
            "redirectUrl": CHECKOUT_URL,
        },
    )


def _status_response(state: str, *, currency: str | None = None) -> httpx.Response:
    payload: dict[str, Any] = {
        "merchantOrderId": MERCHANT_ORDER_ID,
        "orderId": PROVIDER_ORDER_ID,
        "state": state,
        "amount": 39_900,
        "expireAt": 1_700_001_200_000,
        "paymentDetails": [],
    }
    if currency is not None:
        payload["currency"] = currency
    return httpx.Response(200, json=payload)


def _client(
    handler: httpx.MockTransport | Any,
    *,
    environment: str = "sandbox",
    clock: Any = lambda: NOW,
    max_response_bytes: int = MAX_PHONEPE_RESPONSE_BYTES,
) -> PhonePeClient:
    transport = (
        handler if isinstance(handler, httpx.MockTransport) else httpx.MockTransport(handler)
    )
    return PhonePeClient(
        environment=environment,
        client_id="client-id",
        client_secret="client-secret",
        client_version="1",
        redirect_url="https://app.example.com/billing/return",
        webhook_username="username",
        webhook_password="password",
        connect_timeout_seconds=1,
        read_timeout_seconds=2,
        order_expire_seconds=1200,
        max_response_bytes=max_response_bytes,
        transport=transport,
        clock=clock,
    )


@pytest.mark.parametrize(
    ("environment", "oauth_url", "payment_url"),
    [
        (
            "sandbox",
            "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token",
            "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay",
        ),
        (
            "production",
            "https://api.phonepe.com/apis/identity-manager/v1/oauth/token",
            "https://api.phonepe.com/apis/pg/checkout/v2/pay",
        ),
    ],
)
def test_auth_and_create_checkout_use_fixed_v2_contract(
    environment: str,
    oauth_url: str,
    payment_url: str,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if str(request.url) == oauth_url:
            assert request.headers["Content-Type"].startswith(
                "application/x-www-form-urlencoded"
            )
            assert parse_qs(request.content.decode()) == {
                "client_id": ["client-id"],
                "client_secret": ["client-secret"],
                "client_version": ["1"],
                "grant_type": ["client_credentials"],
            }
            return _token_response()
        assert str(request.url) == payment_url
        assert request.headers["Authorization"] == "O-Bearer oauth-token"
        assert json.loads(request.content) == {
            "merchantOrderId": MERCHANT_ORDER_ID,
            "amount": 39_900,
            "expireAfter": 1200,
            "paymentFlow": {
                "type": "PG_CHECKOUT",
                "merchantUrls": {
                    "redirectUrl": "https://app.example.com/billing/return"
                },
            },
        }
        return _checkout_response()

    with _client(handler, environment=environment) as client:
        checkout = client.create_checkout(
            merchant_order_id=MERCHANT_ORDER_ID,
            amount_paise=39_900,
            currency="INR",
        )

    assert checkout.merchant_order_id == MERCHANT_ORDER_ID
    assert checkout.provider_order_id == PROVIDER_ORDER_ID
    assert checkout.redirect_url == CHECKOUT_URL
    assert checkout.state is PhonePeOrderState.PENDING
    assert checkout.expire_at == 1_700_001_200_000
    assert len(requests) == 2


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("PENDING", PhonePeOrderState.PENDING),
        ("COMPLETED", PhonePeOrderState.COMPLETED),
        ("FAILED", PhonePeOrderState.FAILED),
    ],
)
def test_get_order_status_accepts_only_documented_states(
    state: str,
    expected: PhonePeOrderState,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/oauth/token"):
            return _token_response()
        assert request.method == "GET"
        assert request.url.path.endswith(f"/checkout/v2/order/{MERCHANT_ORDER_ID}/status")
        assert dict(request.url.params) == {
            "details": "false",
            "errorContext": "false",
        }
        assert request.headers["Authorization"] == "O-Bearer oauth-token"
        return _status_response(state, currency="INR")

    with _client(handler) as client:
        status = client.get_order_status(MERCHANT_ORDER_ID)

    assert status.merchant_order_id == MERCHANT_ORDER_ID
    assert status.provider_order_id == PROVIDER_ORDER_ID
    assert status.state is expected
    assert status.amount_paise == 39_900
    assert status.currency == "INR"
    assert status.expire_at == 1_700_001_200_000


def test_token_is_cached_until_expiry_skew_then_refetched() -> None:
    now = [NOW]
    auth_calls = 0
    status_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal auth_calls, status_calls
        if request.url.path.endswith("/v1/oauth/token"):
            auth_calls += 1
            return _token_response(token=f"token-{auth_calls}", expires_at=NOW + 120)
        status_calls += 1
        expected_token = "token-1" if status_calls < 3 else "token-2"
        assert request.headers["Authorization"] == f"O-Bearer {expected_token}"
        return _status_response("PENDING")

    with _client(handler, clock=lambda: now[0]) as client:
        client.get_order_status(MERCHANT_ORDER_ID)
        now[0] = NOW + 59
        client.get_order_status(MERCHANT_ORDER_ID)
        now[0] = NOW + 60
        client.get_order_status(MERCHANT_ORDER_ID)

    assert auth_calls == 2
    assert status_calls == 3


def test_token_cache_lock_prevents_concurrent_duplicate_auth_requests() -> None:
    lock = threading.Lock()
    auth_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal auth_calls
        if request.url.path.endswith("/v1/oauth/token"):
            with lock:
                auth_calls += 1
            time.sleep(0.02)
            return _token_response()
        return _status_response("PENDING")

    with _client(handler) as client, ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(client.get_order_status, [MERCHANT_ORDER_ID] * 8))

    assert auth_calls == 1
    assert all(result.state is PhonePeOrderState.PENDING for result in results)


def test_create_checkout_timeout_is_sanitized_and_not_retried() -> None:
    payment_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal payment_calls
        if request.url.path.endswith("/v1/oauth/token"):
            return _token_response()
        payment_calls += 1
        raise httpx.ReadTimeout("secret response body", request=request)

    with _client(handler) as client, pytest.raises(PhonePeProviderError) as captured:
        client.create_checkout(
            merchant_order_id=MERCHANT_ORDER_ID,
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category is PhonePeFailureCategory.TIMEOUT
    assert captured.value.retryable is True
    assert "secret" not in str(captured.value)
    assert captured.value.__cause__ is None
    assert payment_calls == 1


@pytest.mark.parametrize(
    ("status_code", "category", "retryable"),
    [
        (401, PhonePeFailureCategory.AUTHENTICATION, False),
        (429, PhonePeFailureCategory.RATE_LIMITED, True),
        (503, PhonePeFailureCategory.UNAVAILABLE, True),
    ],
)
def test_provider_http_failures_are_fixed_sanitized_errors_without_create_retry(
    status_code: int,
    category: PhonePeFailureCategory,
    retryable: bool,
) -> None:
    payment_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal payment_calls
        if request.url.path.endswith("/v1/oauth/token"):
            return _token_response()
        payment_calls += 1
        return httpx.Response(status_code, text="provider-secret-body")

    with _client(handler) as client, pytest.raises(PhonePeProviderError) as captured:
        client.create_checkout(
            merchant_order_id=MERCHANT_ORDER_ID,
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category is category
    assert captured.value.retryable is retryable
    assert str(captured.value) == f"PhonePe request failed ({category.value})."
    assert payment_calls == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"orderId": PROVIDER_ORDER_ID, "state": "UNKNOWN"}),
        httpx.Response(
            200,
            json={
                "orderId": PROVIDER_ORDER_ID,
                "state": "PENDING",
                "expireAt": 1_700_001_200_000,
                "redirectUrl": "javascript:alert(1)",
            },
        ),
        httpx.Response(
            200,
            json={
                "orderId": PROVIDER_ORDER_ID,
                "state": "PENDING",
                "expireAt": 1_700_001_200_000,
                "redirectUrl": "https://payments.attacker.example/collect",
            },
        ),
        httpx.Response(
            200,
            json={
                "orderId": PROVIDER_ORDER_ID,
                "state": "PENDING",
                "expireAt": 10**100,
                "redirectUrl": CHECKOUT_URL,
            },
        ),
    ],
)
def test_malformed_checkout_schema_is_rejected_without_exposing_body(
    response: httpx.Response,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/oauth/token"):
            return _token_response()
        return response

    with _client(handler) as client, pytest.raises(PhonePeProviderError) as captured:
        client.create_checkout(
            merchant_order_id=MERCHANT_ORDER_ID,
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category is PhonePeFailureCategory.INVALID_RESPONSE
    assert captured.value.retryable is False
    assert "javascript" not in str(captured.value)


def test_oversized_provider_json_is_rejected_before_parsing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/oauth/token"):
            return _token_response()
        return httpx.Response(
            200,
            content=b'{' + b'"padding":"' + b"x" * MAX_PHONEPE_RESPONSE_BYTES + b'"}',
        )

    with _client(handler) as client, pytest.raises(PhonePeProviderError) as captured:
        client.create_checkout(
            merchant_order_id=MERCHANT_ORDER_ID,
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category is PhonePeFailureCategory.INVALID_RESPONSE


def test_caller_supplied_order_amount_and_currency_are_validated_before_io() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _token_response()

    with _client(handler) as client:
        with pytest.raises(PhonePeRequestError):
            client.create_checkout(
                merchant_order_id="bad/order",
                amount_paise=39_900,
                currency="INR",
            )
        with pytest.raises(PhonePeRequestError):
            client.create_checkout(
                merchant_order_id=MERCHANT_ORDER_ID,
                amount_paise=99,
                currency="INR",
            )
        with pytest.raises(PhonePeRequestError):
            client.create_checkout(
                merchant_order_id=MERCHANT_ORDER_ID,
                amount_paise=39_900,
                currency="USD",
            )

    assert calls == 0


def test_callback_authorization_matches_official_sdk_vector() -> None:
    official_vector = "bc842c31a9e54efe320d30d948be61291f3ceee4766e36ab25fa65243cd76e0e"

    assert validate_callback_authorization("username", "password", official_vector)
    assert not validate_callback_authorization("username", "password", "0" * 64)

    with _client(lambda _request: _token_response()) as client:
        assert client.verify_callback_authorization(official_vector)
        assert not client.verify_callback_authorization(official_vector.upper())
