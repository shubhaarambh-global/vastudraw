from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from ai_vastu.billing import (
    BillingService,
    PaymentOrder,
    PaymentOrderConflictError,
    PaymentOrderStatus,
    PhonePeClient,
    PhonePeConfigurationError,
    PhonePeFailureCategory,
    PhonePeOrderState,
    PhonePeOrderStatus,
    PhonePeProviderError,
    ProductKind,
    RazorpayClient,
    create_billing_repository,
    get_product,
    public_catalog,
)
from ai_vastu.billing.phonepe_factory import create_phonepe_client
from ai_vastu.billing.repository import BillingRepository
from ai_vastu.production.settings import load_production_settings
from app.auth_dependencies import CurrentUserDependency, project_service, require_project_owner

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    sku: str


MAX_PAYMENT_WEBHOOK_BYTES = 256 * 1024


def _strict_json_object(raw_body: bytes) -> dict[str, Any]:
    def reject_constant(_value: str) -> NoReturn:
        raise ValueError("Non-finite JSON constant.")

    def parse_finite_float(raw_value: str) -> float:
        result = float(raw_value)
        if not math.isfinite(result):
            raise ValueError("Non-finite JSON number.")
        return result

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key.")
            result[key] = value
        return result

    value = json.loads(
        raw_body,
        parse_constant=reject_constant,
        parse_float=parse_finite_float,
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError("Webhook payload must be an object.")
    return value


async def _bounded_webhook_body(request: Request) -> bytes:
    raw_length = request.headers.get("content-length")
    if raw_length is not None:
        try:
            declared_length = int(raw_length)
            if declared_length < 0:
                raise ValueError
            if declared_length > MAX_PAYMENT_WEBHOOK_BYTES:
                raise HTTPException(status_code=413, detail="Payment webhook is too large.")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid content length.") from exc
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_PAYMENT_WEBHOOK_BYTES:
            raise HTTPException(status_code=413, detail="Payment webhook is too large.")
        body.extend(chunk)
    return bytes(body)


def _selected_gateway() -> str:
    return (
        load_production_settings().payment_gateway
        if os.getenv("APP_ENV", "development").strip().lower() == "production"
        else os.getenv("AI_VASTU_PAYMENT_GATEWAY", "disabled").strip().lower()
    )


def _require_razorpay_gateway() -> None:
    if _selected_gateway() != "razorpay":
        raise HTTPException(
            status_code=503,
            detail="Razorpay payments are unavailable for the selected gateway.",
        )


def _require_phonepe_gateway() -> None:
    if _selected_gateway() != "phonepe":
        raise HTTPException(
            status_code=503,
            detail="PhonePe payments are unavailable for the selected gateway.",
        )


def _phonepe_client() -> PhonePeClient:
    return create_phonepe_client()


def _checkout_payload(order: PaymentOrder) -> dict[str, object]:
    return {
        "merchant_order_id": order.merchant_order_id,
        "sku": order.sku,
        "provider": order.provider,
        "provider_reference_id": order.provider_order_id,
        "checkout_url": order.checkout_url,
        "status": order.status.value,
        "amount_paise": order.amount_paise,
        "currency": order.currency,
    }


def _idempotency_digest(user_id: str, value: str | None) -> str:
    if value is None or not 8 <= len(value) <= 128 or value.strip() != value:
        raise HTTPException(
            status_code=400,
            detail="A valid Idempotency-Key header is required.",
        )
    return hashlib.sha256(f"{user_id}\0{value}".encode()).hexdigest()


def _service() -> tuple[BillingService, BillingRepository]:
    repository = create_billing_repository()
    return BillingService(repository), repository


@router.get("/catalog")
def catalog() -> dict[str, object]:
    return {"currency": "INR", "products": public_catalog()}


@router.get("/me")
def billing_me(
    user: CurrentUserDependency,
) -> dict[str, object]:
    user_id = str(user.user_id)
    service, repository = _service()
    try:
        snapshot = service.snapshot(user_id)
        return {
            "user_id": snapshot.user_id,
            "free_generation_available": snapshot.free_generation_available,
            "project_credits": snapshot.project_credits,
            "active_subscription_sku": snapshot.active_subscription_sku,
            "subscription_status": snapshot.subscription_status.value,
            "subscription_period_end": (
                snapshot.subscription_period_end.isoformat()
                if snapshot.subscription_period_end
                else None
            ),
        }
    finally:
        repository.close()


@router.post("/projects/{project_id}/register")
def register_project_entitlement(
    project_id: UUID,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, str]:
    require_project_owner(project_service(request), project_id, user)
    user_id = str(user.user_id)
    project_id_str = str(project_id)
    service, repository = _service()
    try:
        source = service.register_project(user_id, project_id_str)
        return {"project_id": project_id_str, "source": source}
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    finally:
        repository.close()


@router.get("/projects/{project_id}/generation-authorization")
def generation_authorization(
    project_id: UUID,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, object]:
    require_project_owner(project_service(request), project_id, user)
    user_id = str(user.user_id)
    project_id_str = str(project_id)
    service, repository = _service()
    try:
        decision = service.authorize_generation(user_id, project_id_str)
        return {
            "project_id": project_id_str,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "consumption": decision.consumption,
        }
    finally:
        repository.close()


@router.post("/projects/{project_id}/generation-succeeded")
def generation_succeeded(
    project_id: UUID,
    request: Request,
    user: CurrentUserDependency,
) -> dict[str, object]:
    require_project_owner(project_service(request), project_id, user)
    user_id = str(user.user_id)
    project_id_str = str(project_id)
    service, repository = _service()
    try:
        service.record_successful_generation(user_id, project_id_str)
        snapshot = service.snapshot(user_id)
        return {
            "project_id": project_id_str,
            "recorded": True,
            "free_generation_available": snapshot.free_generation_available,
            "project_credits": snapshot.project_credits,
        }
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    finally:
        repository.close()


@router.post("/checkout")
def create_checkout(
    request: CheckoutRequest,
    user: CurrentUserDependency,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, object]:
    user_id = str(user.user_id)
    gateway = _selected_gateway()
    if gateway not in {"phonepe", "razorpay"}:
        raise HTTPException(status_code=503, detail="Payments are unavailable.")
    try:
        product = get_product(request.sku)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown billing SKU.") from exc
    if product.kind == ProductKind.FREE:
        raise HTTPException(status_code=400, detail="The free plan does not use checkout.")
    if product.kind == ProductKind.SUBSCRIPTION:
        raise HTTPException(
            status_code=409,
            detail="Recurring subscription checkout is not available for this gateway.",
        )
    digest = _idempotency_digest(user_id, idempotency_key)
    merchant_order_id = f"vd_{uuid4().hex}"
    service, repository = _service()
    try:
        order, created = service.create_or_get_payment_order(
            merchant_order_id=merchant_order_id,
            idempotency_key=digest,
            user_id=user_id,
            sku=request.sku,
            provider=gateway,
        )
        if not created:
            return _checkout_payload(order)

        if gateway == "phonepe":
            try:
                with _phonepe_client() as client:
                    checkout = client.create_checkout(
                        merchant_order_id=order.merchant_order_id,
                        amount_paise=order.amount_paise,
                        currency=order.currency,
                    )
            except PhonePeProviderError as exc:
                marker = exc.category.value
                if exc.retryable or exc.category == PhonePeFailureCategory.INVALID_RESPONSE:
                    service.mark_checkout_unknown(
                        provider=gateway,
                        merchant_order_id=order.merchant_order_id,
                        failure_code=marker,
                    )
                else:
                    service.mark_checkout_failed(
                        provider=gateway,
                        merchant_order_id=order.merchant_order_id,
                        failure_code=marker,
                    )
                raise HTTPException(
                    status_code=503, detail="PhonePe checkout is temporarily unavailable."
                ) from exc
            except (PhonePeConfigurationError, ValueError) as exc:
                service.mark_checkout_failed(
                    provider=gateway,
                    merchant_order_id=order.merchant_order_id,
                    failure_code="configuration",
                )
                raise HTTPException(
                    status_code=503, detail="PhonePe checkout is not configured."
                ) from exc
            order = service.mark_checkout_created(
                provider=gateway,
                merchant_order_id=order.merchant_order_id,
                provider_order_id=checkout.provider_order_id,
                checkout_url=checkout.redirect_url,
                expires_at=datetime.fromtimestamp(checkout.expire_at / 1000, tz=UTC),
            )
            return _checkout_payload(order)

        try:
            session = RazorpayClient.from_environment().create_checkout(
                user_id=user_id,
                sku=request.sku,
                reference_id=order.merchant_order_id,
                callback_url=None,
            )
        except (ValueError, RuntimeError) as exc:
            service.mark_checkout_unknown(
                provider=gateway,
                merchant_order_id=order.merchant_order_id,
                failure_code="provider_error",
            )
            raise HTTPException(
                status_code=503, detail="Razorpay checkout is temporarily unavailable."
            ) from exc
        order = service.mark_checkout_created(
            provider=gateway,
            merchant_order_id=order.merchant_order_id,
            provider_order_id=session.provider_reference_id,
            checkout_url=session.checkout_url,
            expires_at=None,
        )
        return _checkout_payload(order)
    except PaymentOrderConflictError as exc:
        raise HTTPException(status_code=409, detail="Idempotency key conflict.") from exc
    finally:
        repository.close()


def _owned_order(service: BillingService, user_id: str, merchant_order_id: str) -> PaymentOrder:
    gateway = _selected_gateway()
    order = service.get_payment_order(gateway, merchant_order_id)
    if order is None or order.user_id != user_id:
        raise HTTPException(status_code=404, detail="Payment order does not exist.")
    return order


def _apply_phonepe_status(
    service: BillingService,
    order: PaymentOrder,
    client: PhonePeClient,
    *,
    event_type: str,
) -> PaymentOrder:
    status = client.get_order_status(order.merchant_order_id)
    return _apply_verified_phonepe_status(
        service, order, status, event_type=event_type
    )


def _apply_verified_phonepe_status(
    service: BillingService,
    order: PaymentOrder,
    status: PhonePeOrderStatus,
    *,
    event_type: str,
) -> PaymentOrder:
    currency = status.currency or order.currency
    if status.amount_paise != order.amount_paise or currency != order.currency:
        service.mark_checkout_unknown(
            provider="phonepe",
            merchant_order_id=order.merchant_order_id,
            failure_code="provider_binding_mismatch",
        )
        raise PaymentOrderConflictError("Provider order binding does not match.")
    if status.state == PhonePeOrderState.COMPLETED:
        service.apply_payment_order_event(
            provider="phonepe",
            event_key=f"{order.merchant_order_id}:completed",
            event_type=event_type,
            merchant_order_id=order.merchant_order_id,
            provider_order_id=status.provider_order_id,
            amount_paise=status.amount_paise,
            currency=currency,
        )
    elif status.state == PhonePeOrderState.FAILED:
        service.mark_checkout_failed(
            provider="phonepe",
            merchant_order_id=order.merchant_order_id,
            failure_code="provider_failed",
        )
    updated = service.get_payment_order("phonepe", order.merchant_order_id)
    assert updated is not None
    return updated


@router.get("/orders/{merchant_order_id}")
def payment_order_status(
    merchant_order_id: str,
    user: CurrentUserDependency,
) -> dict[str, object]:
    service, repository = _service()
    try:
        return _checkout_payload(_owned_order(service, str(user.user_id), merchant_order_id))
    finally:
        repository.close()


@router.post("/orders/{merchant_order_id}/refresh")
def refresh_payment_order(
    merchant_order_id: str,
    user: CurrentUserDependency,
) -> dict[str, object]:
    _require_phonepe_gateway()
    service, repository = _service()
    try:
        order = _owned_order(service, str(user.user_id), merchant_order_id)
        if order.status in {
            PaymentOrderStatus.CHECKOUT_FAILED,
            PaymentOrderStatus.FULFILLED,
        }:
            return _checkout_payload(order)
        with _phonepe_client() as client:
            return _checkout_payload(
                _apply_phonepe_status(
                    service,
                    order,
                    client,
                    event_type="authenticated_status_refresh",
                )
            )
    except PhonePeProviderError as exc:
        raise HTTPException(
            status_code=503, detail="Payment status is temporarily unavailable."
        ) from exc
    except PaymentOrderConflictError as exc:
        raise HTTPException(
            status_code=409, detail="Payment status did not match the order."
        ) from exc
    except (PhonePeConfigurationError, ValueError) as exc:
        raise HTTPException(
            status_code=503, detail="PhonePe status is not configured."
        ) from exc
    finally:
        repository.close()


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
) -> dict[str, object]:
    _require_razorpay_gateway()
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing Razorpay signature.")
    raw_body = await _bounded_webhook_body(request)

    try:
        client = RazorpayClient.from_environment()
        valid = client.verify_webhook_signature(raw_body, x_razorpay_signature)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail="Razorpay webhook verification is unavailable."
        ) from exc
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature.")

    try:
        payload = _strict_json_object(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.") from exc

    event_type = str(payload.get("event", ""))
    service, repository = _service()
    try:
        if event_type == "payment_link.paid":
            entity = payload["payload"]["payment_link"]["entity"]
            merchant_order_id = str(entity["reference_id"])
            order = service.get_payment_order("razorpay", merchant_order_id)
            if order is None:
                return {"ok": True, "applied": False, "ignored": "unknown_order"}
            changed = service.apply_payment_order_event(
                provider="razorpay",
                event_key=f"{merchant_order_id}:paid",
                event_type=event_type,
                merchant_order_id=merchant_order_id,
                provider_order_id=str(entity["id"]),
                amount_paise=int(entity["amount"]),
                currency=str(entity["currency"]),
            )
            return {"ok": True, "applied": changed}

        if event_type.startswith("subscription."):
            return {"ok": True, "applied": False, "ignored": "subscription_unavailable"}

        return {"ok": True, "applied": False, "ignored": event_type}
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Malformed billing webhook.") from exc
    finally:
        repository.close()


@router.post("/webhooks/phonepe")
async def phonepe_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_phonepe_gateway()
    if not authorization:
        raise HTTPException(status_code=400, detail="Missing PhonePe authorization.")
    raw_body = await _bounded_webhook_body(request)

    try:
        client = _phonepe_client()
    except (PhonePeConfigurationError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="PhonePe webhook is not configured.") from exc
    try:
        if not client.verify_callback_authorization(authorization):
            raise HTTPException(status_code=400, detail="Invalid PhonePe authorization.")
        try:
            payload = _strict_json_object(raw_body)
            event_type = str(payload["event"])
            body = payload["payload"]
            if not isinstance(body, dict):
                raise ValueError("PhonePe payload must be an object.")
            merchant_order_id = str(body["merchantOrderId"])
            if (
                not 1 <= len(merchant_order_id) <= 63
                or not merchant_order_id.replace("-", "").replace("_", "").isalnum()
            ):
                raise ValueError("PhonePe merchant order ID is invalid.")
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            RecursionError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise HTTPException(status_code=400, detail="Malformed PhonePe webhook.") from exc
        if event_type not in {"checkout.order.completed", "checkout.order.failed"}:
            return {"ok": True, "applied": False, "ignored": event_type}

        service, repository = _service()
        try:
            order = service.get_payment_order("phonepe", merchant_order_id)
            if order is None:
                return {"ok": True, "applied": False, "ignored": "unknown_order"}
            if order.status in {
                PaymentOrderStatus.CHECKOUT_FAILED,
                PaymentOrderStatus.FULFILLED,
            }:
                return {
                    "ok": True,
                    "applied": False,
                    "status": order.status.value,
                }
            before = order.status
            provider_status = await run_in_threadpool(
                client.get_order_status, order.merchant_order_id
            )
            updated = _apply_verified_phonepe_status(
                service,
                order,
                provider_status,
                event_type=event_type,
            )
            return {
                "ok": True,
                "applied": before != updated.status,
                "status": updated.status.value,
            }
        except PaymentOrderConflictError as exc:
            raise HTTPException(
                status_code=409, detail="PhonePe status did not match the payment order."
            ) from exc
        finally:
            repository.close()
    except PhonePeProviderError as exc:
        raise HTTPException(
            status_code=503, detail="PhonePe status is temporarily unavailable."
        ) from exc
    finally:
        client.close()
