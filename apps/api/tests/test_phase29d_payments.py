from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ai_vastu.auth import AuthenticatedUser
from ai_vastu.billing.phonepe import (
    PhonePeCheckout,
    PhonePeConfigurationError,
    PhonePeFailureCategory,
    PhonePeOrderState,
    PhonePeOrderStatus,
    PhonePeProviderError,
)
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository
from app import billing_routes
from app.main import create_app

USER = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("22222222-2222-2222-2222-222222222222")
AUTH = {"Authorization": "Bearer payment-test-token", "Idempotency-Key": "checkout-001"}
CALLBACK_AUTH = hashlib.sha256(b"username:password").hexdigest()


class FakePhonePeClient:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.create_calls = 0
        self.status_calls = 0
        self.create_error: PhonePeProviderError | None = None
        self.status = PhonePeOrderStatus(
            merchant_order_id="unset",
            provider_order_id="OMO_PROVIDER_1",
            state=PhonePeOrderState.COMPLETED,
            amount_paise=39_900,
            currency="INR",
            expire_at=2_000_000_000_000,
        )

    def __enter__(self) -> FakePhonePeClient:
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
        repository = SqliteBillingRepository(self.database_path)
        try:
            persisted = repository.get_payment_order("phonepe", merchant_order_id)
            assert persisted is not None
            assert persisted.amount_paise == amount_paise == 39_900
            assert persisted.currency == currency == "INR"
        finally:
            repository.close()
        if self.create_error is not None:
            raise self.create_error
        return PhonePeCheckout(
            merchant_order_id=merchant_order_id,
            provider_order_id="OMO_PROVIDER_1",
            redirect_url="https://mercury-uat.phonepe.com/pay/token",
            state=PhonePeOrderState.PENDING,
            expire_at=2_000_000_000_000,
        )

    def get_order_status(self, merchant_order_id: str) -> PhonePeOrderStatus:
        self.status_calls += 1
        return PhonePeOrderStatus(
            merchant_order_id=merchant_order_id,
            provider_order_id=self.status.provider_order_id,
            state=self.status.state,
            amount_paise=self.status.amount_paise,
            currency=self.status.currency,
            expire_at=self.status.expire_at,
        )


def _client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[TestClient, Path, FakePhonePeClient, MagicMock]:
    database_path = tmp_path / "phase29d.sqlite3"
    fake_phonepe = FakePhonePeClient(database_path)
    verifier = MagicMock()
    verifier.verify.return_value = AuthenticatedUser(user_id=USER, role="authenticated")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", "phonepe")
    monkeypatch.setattr(
        billing_routes,
        "create_billing_repository",
        lambda: SqliteBillingRepository(database_path),
    )
    monkeypatch.setattr(billing_routes, "_phonepe_client", lambda: fake_phonepe)
    client = TestClient(
        create_app(
            repository=MagicMock(),
            access_token_verifier=verifier,
            generation_intake_store=MagicMock(),
        )
    )
    return client, database_path, fake_phonepe, verifier


def test_phonepe_checkout_persists_before_provider_and_replays_idempotently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, phonepe, _ = _client(monkeypatch, tmp_path)

    first = client.post("/billing/checkout", headers=AUTH, json={"sku": "project_single"})
    replay = client.post("/billing/checkout", headers=AUTH, json={"sku": "project_single"})

    assert first.status_code == 200
    assert first.json()["amount_paise"] == 39_900
    assert first.json()["status"] == "checkout_created"
    assert replay.status_code == 200
    assert replay.json()["merchant_order_id"] == first.json()["merchant_order_id"]
    assert phonepe.create_calls == 1


def test_malformed_successful_create_stays_reconcilable_and_fulfils_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, phonepe, _ = _client(monkeypatch, tmp_path)
    phonepe.create_error = PhonePeProviderError(PhonePeFailureCategory.INVALID_RESPONSE)

    checkout = client.post(
        "/billing/checkout", headers=AUTH, json={"sku": "project_single"}
    )
    assert checkout.status_code == 503

    repository = SqliteBillingRepository(database_path)
    try:
        orders = repository.list_reconcilable_payment_orders("phonepe", 10)
        assert len(orders) == 1
        order = orders[0]
        assert order.status.value == "checkout_unknown"
    finally:
        repository.close()

    phonepe.create_error = None
    callback = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json={
            "event": "checkout.order.completed",
            "payload": {"merchantOrderId": order.merchant_order_id},
        },
    )
    replay = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json={
            "event": "checkout.order.completed",
            "payload": {"merchantOrderId": order.merchant_order_id},
        },
    )

    assert callback.status_code == 200
    assert callback.json()["status"] == "fulfilled"
    assert replay.status_code == 200
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 1
    finally:
        repository.close()


def test_checkout_rejects_free_subscription_unknown_and_missing_idempotency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, phonepe, _ = _client(monkeypatch, tmp_path)

    assert (
        client.post(
            "/billing/checkout", headers=AUTH, json={"sku": "pro_monthly"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/billing/checkout", headers=AUTH, json={"sku": "pro_yearly"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/billing/checkout", headers=AUTH, json={"sku": "free_first_generation"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/billing/checkout", headers=AUTH, json={"sku": "missing"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/billing/checkout",
            headers={"Authorization": AUTH["Authorization"]},
            json={"sku": "project_single"},
        ).status_code
        == 400
    )
    assert phonepe.create_calls == 0


def test_phonepe_callback_reconciles_status_and_applies_entitlement_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, phonepe, _ = _client(monkeypatch, tmp_path)
    checkout = client.post(
        "/billing/checkout", headers=AUTH, json={"sku": "project_single"}
    ).json()
    callback = {
        "event": "checkout.order.completed",
        "payload": {
            "merchantOrderId": checkout["merchant_order_id"],
            "state": "COMPLETED",
            "amount": 1,
            "metaInfo": {"udf1": str(OTHER), "udf2": "pro_yearly"},
        },
    }

    first = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json=callback,
    )
    replay = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json=callback,
    )

    assert first.status_code == 200
    assert first.json()["status"] == "fulfilled"
    assert replay.status_code == 200
    assert phonepe.status_calls == 1
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 1
        assert repository.get_snapshot(str(OTHER)).project_credits == 0
    finally:
        repository.close()


def test_phonepe_callback_rejects_missing_auth_and_status_amount_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, phonepe, _ = _client(monkeypatch, tmp_path)
    checkout = client.post(
        "/billing/checkout", headers=AUTH, json={"sku": "project_single"}
    ).json()
    callback = {
        "event": "checkout.order.completed",
        "payload": {"merchantOrderId": checkout["merchant_order_id"]},
    }

    assert client.post("/billing/webhooks/phonepe", json=callback).status_code == 400
    phonepe.status = PhonePeOrderStatus(
        merchant_order_id="unset",
        provider_order_id="OMO_PROVIDER_1",
        state=PhonePeOrderState.COMPLETED,
        amount_paise=39_901,
        currency="INR",
        expire_at=2_000_000_000_000,
    )
    mismatch = client.post(
        "/billing/webhooks/phonepe",
        headers={"Authorization": CALLBACK_AUTH},
        json=callback,
    )
    assert mismatch.status_code == 409
    refresh_mismatch = client.post(
        f"/billing/orders/{checkout['merchant_order_id']}/refresh", headers=AUTH
    )
    assert refresh_mismatch.status_code == 409
    assert refresh_mismatch.json() == {
        "detail": "Payment status did not match the order."
    }
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 0
    finally:
        repository.close()


def test_payment_order_read_is_owner_scoped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, _, verifier = _client(monkeypatch, tmp_path)
    order_id = client.post(
        "/billing/checkout", headers=AUTH, json={"sku": "project_single"}
    ).json()["merchant_order_id"]

    assert client.get(f"/billing/orders/{order_id}", headers=AUTH).status_code == 200
    verifier.verify.return_value = AuthenticatedUser(user_id=OTHER, role="authenticated")
    assert client.get(f"/billing/orders/{order_id}", headers=AUTH).status_code == 404


def test_provider_failed_status_is_terminal_without_entitlement(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, database_path, phonepe, _ = _client(monkeypatch, tmp_path)
    checkout = client.post(
        "/billing/checkout", headers=AUTH, json={"sku": "project_single"}
    ).json()
    phonepe.status = PhonePeOrderStatus(
        merchant_order_id="unset",
        provider_order_id="OMO_PROVIDER_1",
        state=PhonePeOrderState.FAILED,
        amount_paise=39_900,
        currency="INR",
        expire_at=2_000_000_000_000,
    )

    response = client.post(
        f"/billing/orders/{checkout['merchant_order_id']}/refresh", headers=AUTH
    )

    assert response.status_code == 200
    assert response.json()["status"] == "checkout_failed"
    second = client.post(
        f"/billing/orders/{checkout['merchant_order_id']}/refresh", headers=AUTH
    )
    assert second.status_code == 200
    assert second.json()["status"] == "checkout_failed"
    assert phonepe.status_calls == 1
    repository = SqliteBillingRepository(database_path)
    try:
        assert repository.get_snapshot(str(USER)).project_credits == 0
    finally:
        repository.close()


def test_phonepe_callback_rejects_oversized_duplicate_and_invalid_order_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, _, _ = _client(monkeypatch, tmp_path)
    headers = {"Authorization": CALLBACK_AUTH, "Content-Type": "application/json"}

    oversized = client.post(
        "/billing/webhooks/phonepe",
        headers=headers,
        content=b"{" + (b" " * (256 * 1024)),
    )
    duplicate = client.post(
        "/billing/webhooks/phonepe",
        headers=headers,
        content=(
            b'{"event":"checkout.order.completed",'
            b'"event":"checkout.order.failed",'
            b'"payload":{"merchantOrderId":"order-1"}}'
        ),
    )
    invalid_order = client.post(
        "/billing/webhooks/phonepe",
        headers=headers,
        json={
            "event": "checkout.order.completed",
            "payload": {"merchantOrderId": "../not-an-order"},
        },
    )

    assert oversized.status_code == 413
    assert duplicate.status_code == 400
    assert invalid_order.status_code == 400


def test_payment_provider_configuration_failures_are_sanitized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, _, _ = _client(monkeypatch, tmp_path)
    checkout = client.post(
        "/billing/checkout", headers=AUTH, json={"sku": "project_single"}
    ).json()
    monkeypatch.setattr(
        billing_routes,
        "_phonepe_client",
        MagicMock(side_effect=PhonePeConfigurationError("secret-shaped-detail")),
    )

    refresh = client.post(
        f"/billing/orders/{checkout['merchant_order_id']}/refresh", headers=AUTH
    )
    assert refresh.status_code == 503
    assert refresh.json() == {"detail": "PhonePe status is not configured."}
    assert "secret-shaped-detail" not in refresh.text

    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", "razorpay")
    monkeypatch.delenv("AI_VASTU_RAZORPAY_KEY_ID", raising=False)
    missing_razorpay = client.post(
        "/billing/webhooks/razorpay",
        headers={"X-Razorpay-Signature": "not-a-signature"},
        json={"event": "payment_link.paid"},
    )
    assert missing_razorpay.status_code == 503
    assert missing_razorpay.json() == {
        "detail": "Razorpay webhook verification is unavailable."
    }


def test_signed_malformed_razorpay_payload_returns_400(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _, _, _ = _client(monkeypatch, tmp_path)
    secret = "synthetic-webhook-secret"
    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", "razorpay")
    monkeypatch.setenv("AI_VASTU_RAZORPAY_KEY_ID", "rzp_test_synthetic")
    monkeypatch.setenv("AI_VASTU_RAZORPAY_KEY_SECRET", "synthetic-key-secret")
    monkeypatch.setenv("AI_VASTU_RAZORPAY_WEBHOOK_SECRET", secret)
    raw_body = json.dumps(
        {"event": "payment_link.paid", "payload": []}, separators=(",", ":")
    ).encode()
    signature = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

    response = client.post(
        "/billing/webhooks/razorpay",
        headers={
            "X-Razorpay-Signature": signature,
            "Content-Type": "application/json",
        },
        content=raw_body,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Malformed billing webhook."}
