from pathlib import Path

import pytest

from ai_vastu.billing.models import SubscriptionStatus
from ai_vastu.billing.service import BillingService
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository

USER = "11111111-1111-1111-1111-111111111111"
PROJECT_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROJECT_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def make_service(tmp_path: Path) -> tuple[BillingService, SqliteBillingRepository]:
    repository = SqliteBillingRepository(tmp_path / "billing.sqlite3")
    return BillingService(repository), repository


def test_free_generation_is_consumed_only_after_success(tmp_path: Path) -> None:
    service, repository = make_service(tmp_path)
    try:
        assert service.register_project(USER, PROJECT_A) == "free_trial_pending"
        auth = service.authorize_generation(USER, PROJECT_A)
        assert auth.allowed
        assert auth.consumption == "free_generation"

        # Merely authorizing does not consume the free generation.
        assert service.snapshot(USER).free_generation_available

        service.record_successful_generation(USER, PROJECT_A)
        assert not service.snapshot(USER).free_generation_available
        assert not service.authorize_generation(USER, PROJECT_A).allowed
    finally:
        repository.close()


def test_single_project_credit_is_bound_once_and_regeneration_is_free(
    tmp_path: Path,
) -> None:
    service, repository = make_service(tmp_path)
    try:
        # Consume the free entitlement first so the paid credit path is unambiguous.
        service.register_project(USER, PROJECT_A)
        service.record_successful_generation(USER, PROJECT_A)

        assert service.apply_one_time_purchase(
            "evt-single", USER, "project_single"
        )
        assert service.snapshot(USER).project_credits == 1

        assert service.register_project(USER, PROJECT_B) == "project_credit"
        assert service.snapshot(USER).project_credits == 0

        for _ in range(3):
            assert service.authorize_generation(USER, PROJECT_B).allowed
            service.record_successful_generation(USER, PROJECT_B)

        assert service.snapshot(USER).project_credits == 0
    finally:
        repository.close()


def test_ten_project_pack_grants_ten_credits_idempotently(tmp_path: Path) -> None:
    service, repository = make_service(tmp_path)
    try:
        assert service.apply_one_time_purchase(
            "evt-pack", USER, "project_pack_10"
        )
        assert not service.apply_one_time_purchase(
            "evt-pack", USER, "project_pack_10"
        )
        assert service.snapshot(USER).project_credits == 10
    finally:
        repository.close()


def test_active_subscription_authorizes_generation(tmp_path: Path) -> None:
    service, repository = make_service(tmp_path)
    try:
        assert service.apply_subscription_event(
            event_key="evt-sub-active",
            event_type="subscription.activated",
            user_id=USER,
            sku="pro_monthly",
            status=SubscriptionStatus.ACTIVE,
            provider_subscription_id="sub_123",
            period_end=None,
        )
        assert service.authorize_generation(USER, PROJECT_A).allowed

        assert service.apply_subscription_event(
            event_key="evt-sub-cancel",
            event_type="subscription.cancelled",
            user_id=USER,
            sku="pro_monthly",
            status=SubscriptionStatus.CANCELLED,
            provider_subscription_id="sub_123",
            period_end=None,
        )
        assert not service.authorize_generation(USER, PROJECT_A).allowed
    finally:
        repository.close()


def test_second_free_project_is_denied(tmp_path: Path) -> None:
    service, repository = make_service(tmp_path)
    try:
        assert service.register_project(USER, PROJECT_A) == "free_trial_pending"
        with pytest.raises(PermissionError):
            service.register_project(USER, PROJECT_B)
    finally:
        repository.close()
