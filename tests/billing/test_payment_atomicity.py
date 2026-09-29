from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from ai_vastu.billing.models import (
    NewPaymentOrder,
    PaymentOrderConflictError,
    PaymentOrderStatus,
)
from ai_vastu.billing.service import BillingService
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository

USER = "11111111-1111-1111-1111-111111111111"
PROVIDER = "phonepe"


def _service(path: Path) -> tuple[BillingService, SqliteBillingRepository]:
    repository = SqliteBillingRepository(path)
    return BillingService(repository), repository


def _create_single_order(
    service: BillingService,
    *,
    merchant_order_id: str = "merchant-1",
    idempotency_key: str = "idempotency-1",
) -> None:
    order, created = service.create_or_get_payment_order(
        merchant_order_id=merchant_order_id,
        idempotency_key=idempotency_key,
        user_id=USER,
        sku="project_single",
        provider=PROVIDER,
    )
    assert created
    assert order.amount_paise == 39_900
    assert order.currency == "INR"


def test_checkout_order_idempotency_returns_the_original_order(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "billing.sqlite3")
    try:
        _create_single_order(service)
        replay, created = service.create_or_get_payment_order(
            merchant_order_id="merchant-retry",
            idempotency_key="idempotency-1",
            user_id=USER,
            sku="project_single",
            provider=PROVIDER,
        )

        assert not created
        assert replay.merchant_order_id == "merchant-1"
        assert replay.user_id == USER

        with pytest.raises(PaymentOrderConflictError):
            service.create_or_get_payment_order(
                merchant_order_id="merchant-conflict",
                idempotency_key="idempotency-1",
                user_id=USER,
                sku="project_pack_10",
                provider=PROVIDER,
            )
    finally:
        repository.close()


def test_repository_rejects_zero_value_paid_order(tmp_path: Path) -> None:
    _, repository = _service(tmp_path / "billing.sqlite3")
    try:
        with pytest.raises(ValueError, match="positive"):
            repository.create_or_get_payment_order(
                NewPaymentOrder(
                    merchant_order_id="merchant-zero",
                    user_id=USER,
                    sku="project_single",
                    provider=PROVIDER,
                    amount_paise=0,
                    currency="INR",
                    idempotency_key="zero-order",
                )
            )
    finally:
        repository.close()


def test_checkout_state_and_reconciliation_scan_are_persisted(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "billing.sqlite3")
    try:
        _create_single_order(service)
        updated = service.mark_checkout_unknown(
            provider=PROVIDER,
            merchant_order_id="merchant-1",
            failure_code="provider_timeout",
        )
        assert updated.status == PaymentOrderStatus.CHECKOUT_UNKNOWN

        updated = service.mark_checkout_created(
            provider=PROVIDER,
            merchant_order_id="merchant-1",
            provider_order_id="provider-order-1",
            checkout_url="https://payments.example/1",
            expires_at=None,
        )
        assert updated.status == PaymentOrderStatus.CHECKOUT_CREATED
        assert updated.failure_code is None

        reconcilable = service.list_reconcilable_payment_orders(PROVIDER, 5000)
        assert [order.merchant_order_id for order in reconcilable] == ["merchant-1"]
    finally:
        repository.close()


def test_payment_event_atomically_fulfils_order_exactly_once(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "billing.sqlite3")
    try:
        _create_single_order(service)
        service.mark_checkout_created(
            provider=PROVIDER,
            merchant_order_id="merchant-1",
            provider_order_id="provider-order-1",
            checkout_url="https://payments.example/1",
            expires_at=None,
        )

        assert service.apply_payment_order_event(
            provider=PROVIDER,
            event_key="event-1",
            event_type="payment.success",
            merchant_order_id="merchant-1",
            provider_order_id="provider-order-1",
            amount_paise=39_900,
            currency="INR",
        )
        assert not service.apply_payment_order_event(
            provider=PROVIDER,
            event_key="event-1",
            event_type="payment.success",
            merchant_order_id="merchant-1",
            provider_order_id="provider-order-1",
            amount_paise=39_900,
            currency="INR",
        )
        assert service.snapshot(USER).project_credits == 1
        order = service.get_payment_order(PROVIDER, "merchant-1")
        assert order is not None
        assert order.status == PaymentOrderStatus.FULFILLED
        assert order.fulfilled_at is not None
        assert service.list_reconcilable_payment_orders(PROVIDER, 10) == []
    finally:
        repository.close()


def test_mismatched_event_rolls_back_and_can_be_retried(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "billing.sqlite3")
    try:
        _create_single_order(service)
        with pytest.raises(PaymentOrderConflictError):
            service.apply_payment_order_event(
                provider=PROVIDER,
                event_key="event-1",
                event_type="payment.success",
                merchant_order_id="merchant-1",
                provider_order_id="provider-order-1",
                amount_paise=1,
                currency="INR",
            )

        assert service.apply_payment_order_event(
            provider=PROVIDER,
            event_key="event-1",
            event_type="payment.success",
            merchant_order_id="merchant-1",
            provider_order_id="provider-order-1",
            amount_paise=39_900,
            currency="INR",
        )
        assert service.snapshot(USER).project_credits == 1
    finally:
        repository.close()


def test_entitlement_failure_rolls_back_event_and_order(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "billing.sqlite3")
    try:
        _create_single_order(service)
        repository._connection.execute(
            """
            CREATE TRIGGER force_credit_failure
            BEFORE UPDATE OF project_credits ON billing_accounts
            BEGIN
                SELECT RAISE(ABORT, 'forced credit failure');
            END
            """
        )
        repository._connection.commit()

        with pytest.raises(sqlite3.IntegrityError, match="forced credit failure"):
            service.apply_payment_order_event(
                provider=PROVIDER,
                event_key="event-rollback",
                event_type="payment.success",
                merchant_order_id="merchant-1",
                provider_order_id="provider-order-1",
                amount_paise=39_900,
                currency="INR",
            )

        order = service.get_payment_order(PROVIDER, "merchant-1")
        assert order is not None
        assert order.status == PaymentOrderStatus.PENDING
        assert service.snapshot(USER).project_credits == 0

        repository._connection.execute(
            "DROP TRIGGER force_credit_failure"
        )
        repository._connection.commit()
        assert service.apply_payment_order_event(
            provider=PROVIDER,
            event_key="event-rollback",
            event_type="payment.success",
            merchant_order_id="merchant-1",
            provider_order_id="provider-order-1",
            amount_paise=39_900,
            currency="INR",
        )
    finally:
        repository.close()


def test_concurrent_event_replay_grants_credits_once(tmp_path: Path) -> None:
    database = tmp_path / "billing.sqlite3"
    service, repository = _service(database)
    _create_single_order(service)
    repository.close()

    def apply_event() -> bool:
        worker_service, worker_repository = _service(database)
        try:
            return worker_service.apply_payment_order_event(
                provider=PROVIDER,
                event_key="event-concurrent",
                event_type="payment.success",
                merchant_order_id="merchant-1",
                provider_order_id="provider-order-1",
                amount_paise=39_900,
                currency="INR",
            )
        finally:
            worker_repository.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: apply_event(), range(2)))

    verification_service, verification_repository = _service(database)
    try:
        assert sorted(results) == [False, True]
        assert verification_service.snapshot(USER).project_credits == 1
    finally:
        verification_repository.close()
