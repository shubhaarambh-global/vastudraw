from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from ai_vastu.billing import (
    BillingService,
    RazorpayClient,
    SubscriptionStatus,
    create_billing_repository,
    public_catalog,
)
from ai_vastu.billing.repository import BillingRepository

router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    sku: str
    callback_url: str | None = None


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer authentication required.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer authentication required.")
    return token


def _resolve_user_id(authorization: str | None) -> str:
    token = _bearer_token(authorization)
    mode = os.getenv("AI_VASTU_AUTH_MODE", "production").strip().lower()

    if mode == "development":
        expected = os.getenv("AI_VASTU_DEV_BEARER_TOKEN", "")
        user_id = os.getenv("AI_VASTU_DEV_USER_ID", "")
        if not expected or not user_id or token != expected:
            raise HTTPException(status_code=401, detail="Invalid development token.")
        return user_id

    supabase_url = os.getenv("AI_VASTU_SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        raise HTTPException(
            status_code=503,
            detail="Supabase authentication is not configured.",
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
        algorithm = str(unverified_header.get("alg", ""))
        if algorithm not in {"RS256", "ES256"}:
            raise ValueError("Unsupported JWT algorithm.")
        jwks = jwt.PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")
        signing_key = jwks.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience=os.getenv("AI_VASTU_SUPABASE_JWT_AUDIENCE", "authenticated"),
            issuer=f"{supabase_url}/auth/v1",
        )
        subject = str(claims["sub"])
        uuid.UUID(subject)
        return subject
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid access token.") from exc


def _service() -> tuple[BillingService, BillingRepository]:
    repository = create_billing_repository()
    return BillingService(repository), repository


@router.get("/catalog")
def catalog() -> dict[str, object]:
    return {"currency": "INR", "products": public_catalog()}


@router.get("/me")
def billing_me(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
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
    project_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    user_id = _resolve_user_id(authorization)
    try:
        uuid.UUID(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid project id.") from exc

    service, repository = _service()
    try:
        source = service.register_project(user_id, project_id)
        return {"project_id": project_id, "source": source}
    except PermissionError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    finally:
        repository.close()


@router.get("/projects/{project_id}/generation-authorization")
def generation_authorization(
    project_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    service, repository = _service()
    try:
        decision = service.authorize_generation(user_id, project_id)
        return {
            "project_id": project_id,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "consumption": decision.consumption,
        }
    finally:
        repository.close()


@router.post("/projects/{project_id}/generation-succeeded")
def generation_succeeded(
    project_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    service, repository = _service()
    try:
        service.record_successful_generation(user_id, project_id)
        snapshot = service.snapshot(user_id)
        return {
            "project_id": project_id,
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
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    user_id = _resolve_user_id(authorization)
    reference_id = f"{request.sku}-{user_id[:8]}-{int(time.time())}"
    try:
        session = RazorpayClient.from_environment().create_checkout(
            user_id=user_id,
            sku=request.sku,
            reference_id=reference_id,
            callback_url=request.callback_url,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {
        "sku": session.sku,
        "provider": session.provider,
        "provider_reference_id": session.provider_reference_id,
        "checkout_url": session.checkout_url,
    }


def _notes(entity: dict[str, Any]) -> dict[str, str]:
    raw = entity.get("notes")
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _subscription_status(event_type: str) -> SubscriptionStatus:
    mapping = {
        "subscription.activated": SubscriptionStatus.ACTIVE,
        "subscription.charged": SubscriptionStatus.ACTIVE,
        "subscription.authenticated": SubscriptionStatus.AUTHENTICATED,
        "subscription.paused": SubscriptionStatus.PAUSED,
        "subscription.halted": SubscriptionStatus.HALTED,
        "subscription.cancelled": SubscriptionStatus.CANCELLED,
        "subscription.completed": SubscriptionStatus.COMPLETED,
    }
    try:
        return mapping[event_type]
    except KeyError as exc:
        raise ValueError("Unsupported subscription event.") from exc


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
) -> dict[str, object]:
    raw_body = await request.body()
    if not x_razorpay_signature:
        raise HTTPException(status_code=400, detail="Missing Razorpay signature.")

    client = RazorpayClient.from_environment()
    try:
        valid = client.verify_webhook_signature(raw_body, x_razorpay_signature)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature.")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook JSON.") from exc

    event_type = str(payload.get("event", ""))
    event_key = hashlib.sha256(raw_body).hexdigest()
    service, repository = _service()
    try:
        if event_type == "payment_link.paid":
            entity = payload["payload"]["payment_link"]["entity"]
            notes = _notes(entity)
            changed = service.apply_one_time_purchase(
                event_key=event_key,
                user_id=notes["user_id"],
                sku=notes["sku"],
            )
            return {"ok": True, "applied": changed}

        if event_type.startswith("subscription."):
            entity = payload["payload"]["subscription"]["entity"]
            notes = _notes(entity)
            current_end = entity.get("current_end")
            period_end = (
                datetime.fromtimestamp(int(current_end), tz=UTC)
                if current_end
                else None
            )
            changed = service.apply_subscription_event(
                event_key=event_key,
                event_type=event_type,
                user_id=notes["user_id"],
                sku=notes["sku"],
                status=_subscription_status(event_type),
                provider_subscription_id=str(entity["id"]),
                period_end=period_end,
            )
            return {"ok": True, "applied": changed}

        return {"ok": True, "applied": False, "ignored": event_type}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Malformed billing webhook.") from exc
    finally:
        repository.close()
