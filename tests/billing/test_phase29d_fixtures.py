from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx
import pytest

from ai_vastu.billing.models import PaymentOrderConflictError
from ai_vastu.billing.phonepe import (
    PhonePeClient,
    PhonePeFailureCategory,
    PhonePeOrderState,
    PhonePeProviderError,
)
from ai_vastu.billing.phonepe_factory import create_phonepe_client
from ai_vastu.billing.service import BillingService
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository

FIXTURE_ROOT = Path(__file__).parents[1] / "fixtures" / "phase29d"


def _fixture(name: str) -> dict[str, Any]:
    value = json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _phonepe_client(handler: Any) -> PhonePeClient:
    return PhonePeClient(
        environment="sandbox",
        client_id="fixture-client-id",
        client_secret="fixture-client-secret",
        client_version="1",
        redirect_url="https://app.example.test/billing/return",
        webhook_username="fixture-webhook-user",
        webhook_password="fixture-webhook-password",
        connect_timeout_seconds=1,
        read_timeout_seconds=2,
        order_expire_seconds=1200,
        transport=httpx.MockTransport(handler),
        clock=lambda: 1_700_000_000.0,
    )


def _service(path: Path) -> tuple[BillingService, SqliteBillingRepository]:
    repository = SqliteBillingRepository(path)
    return BillingService(repository), repository


def _create_fixture_order(
    service: BillingService, fixture: dict[str, Any], provider: str = "phonepe"
) -> None:
    _, created = service.create_or_get_payment_order(
        merchant_order_id=str(fixture["merchant_order_id"]),
        idempotency_key=str(fixture["idempotency_key"]),
        user_id=str(fixture["user_id"]),
        sku=str(fixture["sku"]),
        provider=provider,
    )
    assert created


def test_phonepe_happy_path_fixture_drives_create_and_status() -> None:
    fixture = _fixture("phonepe_responses.json")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/oauth/token"):
            return httpx.Response(200, json=fixture["oauth"])
        if request.method == "POST":
            return httpx.Response(200, json=fixture["checkout"])
        return httpx.Response(200, json=fixture["status"])

    with _phonepe_client(handler) as client:
        checkout = client.create_checkout(
            merchant_order_id="vd_fixture_order_001",
            amount_paise=39_900,
            currency="INR",
        )
        status = client.get_order_status("vd_fixture_order_001")

    assert checkout.provider_order_id == "OMO_FIXTURE_001"
    assert checkout.state is PhonePeOrderState.PENDING
    assert status.state is PhonePeOrderState.COMPLETED
    assert status.amount_paise == 39_900
    assert status.currency == "INR"


@pytest.mark.parametrize("failure_index", range(4))
def test_phonepe_http_failure_fixtures_are_sanitized(failure_index: int) -> None:
    fixture = _fixture("phonepe_responses.json")
    failure = fixture["http_failures"][failure_index]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/oauth/token"):
            return httpx.Response(200, json=fixture["oauth"])
        return httpx.Response(int(failure["status"]), text="fixture-sensitive-body")

    with _phonepe_client(handler) as client, pytest.raises(
        PhonePeProviderError
    ) as captured:
        client.create_checkout(
            merchant_order_id="vd_fixture_order_001",
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category.value == failure["category"]
    assert captured.value.retryable is failure["retryable"]
    assert "sensitive" not in str(captured.value)


def test_phonepe_timeout_fixture_is_sanitized_and_not_retried() -> None:
    fixture = _fixture("phonepe_responses.json")
    checkout_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal checkout_calls
        if request.url.path.endswith("/v1/oauth/token"):
            return httpx.Response(200, json=fixture["oauth"])
        checkout_calls += 1
        raise httpx.ReadTimeout("fixture-sensitive-timeout", request=request)

    with _phonepe_client(handler) as client, pytest.raises(
        PhonePeProviderError
    ) as captured:
        client.create_checkout(
            merchant_order_id="vd_fixture_order_001",
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category is PhonePeFailureCategory.TIMEOUT
    assert "sensitive" not in str(captured.value)
    assert checkout_calls == 1


@pytest.mark.parametrize("body_index", range(4))
def test_phonepe_malformed_and_duplicate_json_fixtures_fail_closed(
    body_index: int,
) -> None:
    fixture = _fixture("phonepe_responses.json")
    body = fixture["invalid_bodies"][body_index].encode()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/oauth/token"):
            return httpx.Response(200, json=fixture["oauth"])
        return httpx.Response(200, content=body)

    with _phonepe_client(handler) as client, pytest.raises(
        PhonePeProviderError
    ) as captured:
        client.create_checkout(
            merchant_order_id="vd_fixture_order_001",
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category is PhonePeFailureCategory.INVALID_RESPONSE


def test_phonepe_oversized_fixture_fails_before_schema_use() -> None:
    fixture = _fixture("phonepe_responses.json")
    body = b'{"padding":"' + b"x" * int(fixture["oversized_padding_bytes"]) + b'"}'

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/oauth/token"):
            return httpx.Response(200, json=fixture["oauth"])
        return httpx.Response(200, content=body)

    with _phonepe_client(handler) as client, pytest.raises(
        PhonePeProviderError
    ) as captured:
        client.create_checkout(
            merchant_order_id="vd_fixture_order_001",
            amount_paise=39_900,
            currency="INR",
        )

    assert captured.value.category is PhonePeFailureCategory.INVALID_RESPONSE


def test_amount_and_currency_mismatch_fixtures_do_not_consume_event(
    tmp_path: Path,
) -> None:
    payment = _fixture("payment_atomicity.json")
    provider = _fixture("phonepe_responses.json")
    service, repository = _service(tmp_path / "fixture-mismatch.sqlite3")
    try:
        _create_fixture_order(service, payment)
        for amount, currency in (
            (provider["mismatches"]["amount"], payment["currency"]),
            (payment["amount_paise"], provider["mismatches"]["currency"]),
        ):
            with pytest.raises(PaymentOrderConflictError):
                service.apply_payment_order_event(
                    provider="phonepe",
                    event_key=str(payment["event_key"]),
                    event_type=str(payment["event_type"]),
                    merchant_order_id=str(payment["merchant_order_id"]),
                    provider_order_id=str(payment["provider_order_id"]),
                    amount_paise=int(amount),
                    currency=str(currency),
                )

        assert service.apply_payment_order_event(
            provider="phonepe",
            event_key=str(payment["event_key"]),
            event_type=str(payment["event_type"]),
            merchant_order_id=str(payment["merchant_order_id"]),
            provider_order_id=str(payment["provider_order_id"]),
            amount_paise=int(payment["amount_paise"]),
            currency=str(payment["currency"]),
        )
        assert service.snapshot(str(payment["user_id"])).project_credits == 1
    finally:
        repository.close()


def test_replay_concurrency_fixture_grants_once(tmp_path: Path) -> None:
    fixture = _fixture("payment_atomicity.json")
    database = tmp_path / "fixture-concurrency.sqlite3"
    service, repository = _service(database)
    _create_fixture_order(service, fixture)
    repository.close()

    def settle(_: int) -> bool:
        worker_service, worker_repository = _service(database)
        try:
            return worker_service.apply_payment_order_event(
                provider="phonepe",
                event_key=str(fixture["event_key"]),
                event_type=str(fixture["event_type"]),
                merchant_order_id=str(fixture["merchant_order_id"]),
                provider_order_id=str(fixture["provider_order_id"]),
                amount_paise=int(fixture["amount_paise"]),
                currency=str(fixture["currency"]),
            )
        finally:
            worker_repository.close()

    workers = int(fixture["concurrency_workers"])
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(settle, range(workers)))

    verification, verification_repository = _service(database)
    try:
        assert results.count(True) == 1
        assert results.count(False) == workers - 1
        assert verification.snapshot(str(fixture["user_id"])).project_credits == 1
    finally:
        verification_repository.close()


def test_provider_namespaces_are_isolated_without_cross_fallback(tmp_path: Path) -> None:
    fixture = _fixture("payment_atomicity.json")
    service, repository = _service(tmp_path / "fixture-providers.sqlite3")
    try:
        for provider in fixture["providers"]:
            _create_fixture_order(service, fixture, provider=str(provider))

        assert service.apply_payment_order_event(
            provider="phonepe",
            event_key=str(fixture["event_key"]),
            event_type=str(fixture["event_type"]),
            merchant_order_id=str(fixture["merchant_order_id"]),
            provider_order_id=str(fixture["provider_order_id"]),
            amount_paise=int(fixture["amount_paise"]),
            currency=str(fixture["currency"]),
        )
        razorpay_order = service.get_payment_order(
            "razorpay", str(fixture["merchant_order_id"])
        )
        assert razorpay_order is not None
        assert razorpay_order.status.value == "pending"
        assert service.snapshot(str(fixture["user_id"])).project_credits == 1
    finally:
        repository.close()


def test_phonepe_factory_is_independent_of_razorpay_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AI_VASTU_PHONEPE_ENVIRONMENT", "sandbox")
    monkeypatch.setenv("AI_VASTU_PHONEPE_CLIENT_ID", "fixture-client-id")
    monkeypatch.setenv("AI_VASTU_PHONEPE_CLIENT_SECRET", "fixture-client-secret")
    monkeypatch.setenv("AI_VASTU_PHONEPE_CLIENT_VERSION", "1")
    monkeypatch.setenv(
        "AI_VASTU_PHONEPE_REDIRECT_URL",
        "https://app.example.test/billing/return",
    )
    monkeypatch.setenv("AI_VASTU_PHONEPE_WEBHOOK_USERNAME", "fixture-webhook-user")
    monkeypatch.setenv("AI_VASTU_PHONEPE_WEBHOOK_PASSWORD", "fixture-webhook-password")
    for name in (
        "AI_VASTU_RAZORPAY_KEY_ID",
        "AI_VASTU_RAZORPAY_KEY_SECRET",
        "AI_VASTU_RAZORPAY_WEBHOOK_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)

    with create_phonepe_client() as client:
        assert isinstance(client, PhonePeClient)
