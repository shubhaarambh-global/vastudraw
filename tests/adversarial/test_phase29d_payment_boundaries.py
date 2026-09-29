from __future__ import annotations

import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from ai_vastu.auth import AuthenticatedUser
from ai_vastu.billing.models import CheckoutSession
from ai_vastu.billing.phonepe import (
    PhonePeCheckout,
    PhonePeConfigurationError,
    PhonePeFailureCategory,
    PhonePeOrderState,
    PhonePeOrderStatus,
    PhonePeProviderError,
)
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository
from ai_vastu.production import middleware as production_middleware
from app import billing_routes, main

USER = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")
BEARER = {"Authorization": "Bearer adversarial-payment-token"}
IDEMPOTENCY = {**BEARER, "Idempotency-Key": "adversarial-checkout-001"}
CALLBACK_AUTH = hashlib.sha256(b"username:password").hexdigest()


class AdversarialPhonePeClient:
    def __init__(self) -> None:
        self.create_calls = 0
        self.status_calls = 0
        self.create_failure: Exception | None = None
        self.status_failure: Exception | None = None
        self.status = PhonePeOrderStatus(
            merchant_order_id="unused",
            provider_order_id="OMO_ADVERSARIAL_1",
            state=PhonePeOrderState.COMPLETED,
            amount_paise=39_900,
            currency="INR",
            expire_at=2_000_000_000_000,
        )

    def __enter__(self) -> AdversarialPhonePeClient:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def close(self) -> None:
        return None

    def verify_callback_authorization(self, authorization: str) -> bool:
        return authorization == CALLBACK_AUTH

    def create_checkout(
        self, *, merchant_order_id: str, amount_paise: int, currency: str
    ) -> PhonePeCheckout:
        self.create_calls += 1
        if self.create_failure is not None:
            raise self.create_failure
        assert amount_paise in {39_900, 339_900}
        assert currency == "INR"
        return PhonePeCheckout(
            merchant_order_id=merchant_order_id,
            provider_order_id="OMO_ADVERSARIAL_1",
            redirect_url="https://mercury-uat.phonepe.com/pay/adversarial-token",
            state=PhonePeOrderState.PENDING,
            expire_at=2_000_000_000_000,
        )

    def get_order_status(self, merchant_order_id: str) -> PhonePeOrderStatus:
        self.status_calls += 1
        if self.status_failure is not None:
            raise self.status_failure
        return PhonePeOrderStatus(
            merchant_order_id=merchant_order_id,
            provider_order_id=self.status.provider_order_id,
            state=self.status.state,
            amount_paise=self.status.amount_paise,
            currency=self.status.currency,
            expire_at=self.status.expire_at,
        )


class AdversarialRazorpayClient:
    def create_checkout(
        self,
        *,
        user_id: str,
        sku: str,
        reference_id: str,
        callback_url: str | None,
    ) -> CheckoutSession:
        del user_id, callback_url
        return CheckoutSession(
            sku=sku,
            provider="razorpay",
            provider_reference_id=f"plink_{reference_id}",
            checkout_url="https://rzp.example.test/adversarial-checkout",
        )

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        del raw_body
        return signature == "valid-signature"


def _development_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    gateway: str = "phonepe",
    raise_server_exceptions: bool = True,
) -> tuple[TestClient, Path, AdversarialPhonePeClient, MagicMock]:
    database_path = tmp_path / "adversarial-phase29d.sqlite3"
    phonepe = AdversarialPhonePeClient()
    verifier = MagicMock()
    verifier.verify.return_value = AuthenticatedUser(user_id=USER, role="authenticated")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", gateway)
    monkeypatch.setattr(
        billing_routes,
        "create_billing_repository",
        lambda: SqliteBillingRepository(database_path),
    )
    monkeypatch.setattr(billing_routes, "_phonepe_client", lambda: phonepe)
    monkeypatch.setattr(
        billing_routes.RazorpayClient,
        "from_environment",
        lambda: AdversarialRazorpayClient(),
    )
    client = TestClient(
        main.create_app(
            repository=MagicMock(),
            access_token_verifier=verifier,
            generation_intake_store=MagicMock(),
        ),
        raise_server_exceptions=raise_server_exceptions,
    )
    return client, database_path, phonepe, verifier


def _checkout(client: TestClient, *, sku: str = "project_single") -> dict[str, object]:
    response = client.post("/billing/checkout", headers=IDEMPOTENCY, json={"sku": sku})
    assert response.status_code == 200
    value = response.json()
    assert isinstance(value, dict)
    return value


def _phonepe_callback(order_id: object) -> dict[str, object]:
    return {
        "event": "checkout.order.completed",
        "payload": {
            "merchantOrderId": order_id,
            "state": "COMPLETED",
            "amount": 1,
            "currency": "USD",
            "metaInfo": {"udf1": str(OTHER), "udf2": "project_pack_10"},
        },
    }


def test_checkout_and_order_routes_require_auth_before_provider_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, phonepe, _ = _development_client(monkeypatch, tmp_path)

    checkout = client.post(
        "/billing/checkout",
        headers={"Idempotency-Key": "adversarial-checkout-001"},
        json={"sku": "project_single"},
    )
    read = client.get("/billing/orders/vd_untrusted")
    refresh = client.post("/billing/orders/vd_untrusted/refresh")

    assert [checkout.status_code, read.status_code, refresh.status_code] == [401, 401, 401]
    assert phonepe.create_calls == 0
    assert phonepe.status_calls == 0


def test_idempotency_conflict_and_cross_user_access_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, phonepe, verifier = _development_client(monkeypatch, tmp_path)
    order = _checkout(client)

    conflict = client.post(
        "/billing/checkout",
        headers=IDEMPOTENCY,
        json={"sku": "project_pack_10"},
    )
    verifier.verify.return_value = AuthenticatedUser(user_id=OTHER, role="authenticated")
    read = client.get(f"/billing/orders/{order['merchant_order_id']}", headers=BEARER)
    refresh = client.post(
        f"/billing/orders/{order['merchant_order_id']}/refresh", headers=BEARER
    )

    assert conflict.status_code == 409
    assert read.status_code == 404
    assert refresh.status_code == 404
    assert phonepe.create_calls == 1
    assert phonepe.status_calls == 0


def test_static_callback_auth_cannot_forge_authoritative_payment_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, phonepe, _ = _development_client(monkeypatch, tmp_path)
    order = _checkout(client)
    phonepe.status = PhonePeOrderStatus(
        merchant_order_id="unused",
        provider_order_id="OMO_ADVERSARIAL_1",
        state=PhonePeOrderState.PENDING,
        amount_paise=39_900,
        currency="INR",
        expire_at=2_000_000_000_000,
    )

    forged = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json=_phonepe_callback(order["merchant_order_id"]),
    )
    invalid_auth = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": "forged-static-auth"},
        json=_phonepe_callback(order["merchant_order_id"]),
    )

    assert forged.status_code == 200
    assert forged.json()["applied"] is False
    assert forged.json()["status"] == "checkout_created"
    assert invalid_auth.status_code == 400
    assert phonepe.status_calls == 1
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 0
        assert repository.get_snapshot(str(OTHER)).project_credits == 0
    finally:
        repository.close()


@pytest.mark.parametrize(
    "body",
    [
        b'{"event":"checkout.order.completed","event":"checkout.order.failed",'
        b'"payload":{"merchantOrderId":"vd_order"}}',
        b'{"event":"checkout.order.completed","payload":'
        b'{"merchantOrderId":"vd_order","amount":NaN}}',
        b'["checkout.order.completed", {"merchantOrderId":"vd_order"}]',
        b"{\xff}",
    ],
)
def test_phonepe_callback_rejects_ambiguous_or_invalid_json_before_status_lookup(
    body: bytes, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, phonepe, _ = _development_client(monkeypatch, tmp_path)

    response = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH, "Content-Type": "application/json"},
        content=body,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Malformed PhonePe webhook."}
    assert phonepe.status_calls == 0


def test_payment_webhooks_reject_oversized_bodies_before_parsing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, phonepe, _ = _development_client(monkeypatch, tmp_path)
    oversized = b"{" + (b"x" * (256 * 1024))

    phonepe_response = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH, "Content-Type": "application/json"},
        content=oversized,
    )
    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", "razorpay")
    razorpay_response = client.post(
        "/billing/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "valid-signature"},
        content=oversized,
    )

    assert phonepe_response.status_code == 413
    assert razorpay_response.status_code == 413
    assert phonepe.status_calls == 0


def test_webhook_streaming_body_stops_reading_at_size_limit() -> None:
    chunk = b"x" * (64 * 1024)
    total_chunks = 10
    received_chunks = 0

    async def exercise() -> tuple[int, int]:
        nonlocal received_chunks

        async def receive() -> dict[str, object]:
            nonlocal received_chunks
            received_chunks += 1
            return {
                "type": "http.request",
                "body": chunk,
                "more_body": received_chunks < total_chunks,
            }

        request = Request(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST",
                "scheme": "https",
                "path": "/billing/webhooks/phonepe",
                "raw_path": b"/billing/webhooks/phonepe",
                "query_string": b"",
                "headers": [],
                "client": ("127.0.0.1", 12345),
                "server": ("api.example.test", 443),
            },
            receive,
        )
        try:
            await billing_routes._bounded_webhook_body(request)
        except HTTPException as exc:
            return exc.status_code, received_chunks
        raise AssertionError("Oversized streaming body was accepted.")

    status_code, chunks_read = asyncio.run(exercise())

    assert status_code == 413
    assert chunks_read <= 5


@pytest.mark.parametrize(
    ("amount", "currency", "provider_order_id"),
    [
        (39_901, "INR", "OMO_ADVERSARIAL_1"),
        (39_900, "USD", "OMO_ADVERSARIAL_1"),
        (39_900, "INR", "OMO_DIFFERENT"),
    ],
)
def test_phonepe_status_must_match_amount_currency_and_provider_order(
    amount: int,
    currency: str,
    provider_order_id: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, database_path, phonepe, _ = _development_client(monkeypatch, tmp_path)
    order = _checkout(client)
    phonepe.status = PhonePeOrderStatus(
        merchant_order_id="unused",
        provider_order_id=provider_order_id,
        state=PhonePeOrderState.COMPLETED,
        amount_paise=amount,
        currency=currency,
        expire_at=2_000_000_000_000,
    )

    response = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json=_phonepe_callback(order["merchant_order_id"]),
    )

    assert response.status_code == 409
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 0
    finally:
        repository.close()


def test_phonepe_configuration_and_provider_failures_do_not_leak_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, phonepe, _ = _development_client(monkeypatch, tmp_path)
    secret = "super-secret-provider-detail"
    monkeypatch.setattr(
        billing_routes,
        "_phonepe_client",
        MagicMock(side_effect=PhonePeConfigurationError(secret)),
    )

    missing_configuration = client.post(
        "/billing/checkout", headers=IDEMPOTENCY, json={"sku": "project_single"}
    )
    assert missing_configuration.status_code == 503
    assert missing_configuration.json() == {"detail": "PhonePe checkout is not configured."}
    assert secret not in missing_configuration.text

    monkeypatch.setattr(billing_routes, "_phonepe_client", lambda: phonepe)
    phonepe.create_failure = PhonePeProviderError(PhonePeFailureCategory.UNAVAILABLE)
    unavailable = client.post(
        "/billing/checkout",
        headers={**BEARER, "Idempotency-Key": "adversarial-checkout-002"},
        json={"sku": "project_single"},
    )
    assert unavailable.status_code == 503
    assert unavailable.json() == {
        "detail": "PhonePe checkout is temporarily unavailable."
    }
    assert secret not in unavailable.text


def test_gateway_selection_never_cross_falls_back_between_providers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, _, _ = _development_client(monkeypatch, tmp_path, gateway="disabled")
    phonepe_factory = MagicMock(side_effect=AssertionError("PhonePe must not be called"))
    razorpay_factory = MagicMock(side_effect=AssertionError("Razorpay must not be called"))
    service_factory = MagicMock(side_effect=AssertionError("Storage must not be opened"))
    monkeypatch.setattr(billing_routes, "_phonepe_client", phonepe_factory)
    monkeypatch.setattr(
        billing_routes.RazorpayClient, "from_environment", razorpay_factory
    )
    monkeypatch.setattr(billing_routes, "_service", service_factory)

    checkout = client.post(
        "/billing/checkout", headers=IDEMPOTENCY, json={"sku": "project_single"}
    )
    phonepe = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json=_phonepe_callback("vd_unknown"),
    )
    razorpay = client.post(
        "/billing/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "valid-signature"},
        json={"event": "payment_link.paid"},
    )

    assert [checkout.status_code, phonepe.status_code, razorpay.status_code] == [503, 503, 503]
    phonepe_factory.assert_not_called()
    razorpay_factory.assert_not_called()
    service_factory.assert_not_called()


def test_razorpay_webhook_ignores_notes_and_binds_persisted_order(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, _, _ = _development_client(
        monkeypatch, tmp_path, gateway="razorpay", raise_server_exceptions=False
    )
    order = _checkout(client)
    order_id = str(order["merchant_order_id"])
    entity = {
        "reference_id": order_id,
        "id": f"plink_{order_id}",
        "amount": 39_900,
        "currency": "INR",
        "notes": {"user_id": str(OTHER), "sku": "project_pack_10"},
    }

    response = client.post(
        "/billing/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "valid-signature"},
        json={"event": "payment_link.paid", "payload": {"payment_link": {"entity": entity}}},
    )

    assert response.status_code == 200
    assert response.json()["applied"] is True
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 1
        assert repository.get_snapshot(str(OTHER)).project_credits == 0
    finally:
        repository.close()


def test_razorpay_binding_mismatch_rolls_back_before_valid_retry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, _, _ = _development_client(
        monkeypatch, tmp_path, gateway="razorpay", raise_server_exceptions=False
    )
    order = _checkout(client)
    order_id = str(order["merchant_order_id"])
    entity = {
        "reference_id": order_id,
        "id": f"plink_{order_id}",
        "amount": 1,
        "currency": "USD",
    }
    payload = {
        "event": "payment_link.paid",
        "payload": {"payment_link": {"entity": entity}},
    }

    mismatch = client.post(
        "/billing/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "valid-signature"},
        json=payload,
    )
    repository = SqliteBillingRepository(database_path)
    try:
        assert mismatch.status_code == 400
        assert repository.get_snapshot(str(USER)).project_credits == 0
    finally:
        repository.close()

    entity.update({"amount": 39_900, "currency": "INR"})
    valid = client.post(
        "/billing/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "valid-signature"},
        json=payload,
    )
    assert valid.status_code == 200
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 1
    finally:
        repository.close()


def test_concurrent_phonepe_callback_replay_grants_exactly_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, _, _ = _development_client(monkeypatch, tmp_path)
    order = _checkout(client)
    callback = _phonepe_callback(order["merchant_order_id"])

    def send_callback(_: int) -> int:
        response = client.post(
            "/billing/webhooks/phonepe",
            headers={"Authorization": CALLBACK_AUTH},
            json=callback,
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=4) as executor:
        statuses = list(executor.map(send_callback, range(8)))

    assert statuses == [200] * 8
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 1
    finally:
        repository.close()


def test_payment_webhook_rate_limit_is_fail_closed_and_cors_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        allowed_origins=("https://app.example.test",),
        trusted_hosts=("api.example.test",),
        payment_gateway="phonepe",
        database_url="postgresql://unused.example.test/vastu",
        rate_limit_interpret_per_hour=20,
        rate_limit_generation_per_hour=10,
        rate_limit_plan_analysis_per_hour=10,
        rate_limit_checkout_per_hour=20,
        rate_limit_payment_status_per_hour=30,
        rate_limit_payment_webhook_per_hour=240,
        hsts_seconds=31_536_000,
    )
    limiter = MagicMock(return_value=SimpleNamespace(allowed=False))
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(main, "load_production_settings", lambda: settings)
    monkeypatch.setattr(production_middleware, "load_production_settings", lambda: settings)
    monkeypatch.setattr(billing_routes, "load_production_settings", lambda: settings)
    monkeypatch.setattr(production_middleware, "consume_postgres_fixed_window", limiter)
    client = TestClient(
        main.create_app(
            repository=MagicMock(),
            access_token_verifier=MagicMock(),
            generation_intake_store=MagicMock(),
        ),
        base_url="https://api.example.test",
    )

    response = client.post(
        "/billing/webhooks/phonepe",
        headers={
            "Authorization": CALLBACK_AUTH,
            "Origin": "https://app.example.test",
        },
        json=_phonepe_callback("vd_unknown"),
    )

    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == "https://app.example.test"
    assert response.json() == {"detail": "Rate limit exceeded."}
    assert limiter.call_args.kwargs["scope"] == "payment_webhook"
    assert limiter.call_args.kwargs["limit"] == 240


def test_payment_webhook_rate_limit_storage_error_is_sanitized_with_cors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "postgres-secret-shaped-detail"
    settings = SimpleNamespace(
        allowed_origins=("https://app.example.test",),
        trusted_hosts=("api.example.test",),
        payment_gateway="phonepe",
        database_url="postgresql://unused.example.test/vastu",
        rate_limit_interpret_per_hour=20,
        rate_limit_generation_per_hour=10,
        rate_limit_plan_analysis_per_hour=10,
        rate_limit_checkout_per_hour=20,
        rate_limit_payment_status_per_hour=30,
        rate_limit_payment_webhook_per_hour=240,
        hsts_seconds=31_536_000,
    )
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(main, "load_production_settings", lambda: settings)
    monkeypatch.setattr(production_middleware, "load_production_settings", lambda: settings)
    monkeypatch.setattr(billing_routes, "load_production_settings", lambda: settings)
    monkeypatch.setattr(
        production_middleware,
        "consume_postgres_fixed_window",
        MagicMock(side_effect=RuntimeError(secret)),
    )
    client = TestClient(
        main.create_app(
            repository=MagicMock(),
            access_token_verifier=MagicMock(),
            generation_intake_store=MagicMock(),
        ),
        base_url="https://api.example.test",
    )

    response = client.post(
        "/billing/webhooks/phonepe",
        headers={
            "Authorization": CALLBACK_AUTH,
            "Origin": "https://app.example.test",
        },
        json=_phonepe_callback("vd_unknown"),
    )

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "https://app.example.test"
    assert response.json() == {"detail": "Rate-limit service unavailable."}
    assert secret not in response.text
