from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Any

import httpx

from .catalog import ProductKind, get_product
from .models import CheckoutSession


class RazorpayConfigurationError(RuntimeError):
    pass


class RazorpayClient:
    API_BASE = "https://api.razorpay.com/v1"

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
        webhook_secret: str,
        monthly_plan_id: str | None = None,
        yearly_plan_id: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not key_id or not key_secret:
            raise RazorpayConfigurationError("Razorpay API credentials are missing.")
        self._key_id = key_id
        self._key_secret = key_secret
        self._webhook_secret = webhook_secret
        self._monthly_plan_id = monthly_plan_id
        self._yearly_plan_id = yearly_plan_id
        self._transport = transport

    @classmethod
    def from_environment(cls) -> RazorpayClient:
        return cls(
            key_id=os.getenv("AI_VASTU_RAZORPAY_KEY_ID", ""),
            key_secret=os.getenv("AI_VASTU_RAZORPAY_KEY_SECRET", ""),
            webhook_secret=os.getenv("AI_VASTU_RAZORPAY_WEBHOOK_SECRET", ""),
            monthly_plan_id=os.getenv("AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID"),
            yearly_plan_id=os.getenv("AI_VASTU_RAZORPAY_YEARLY_PLAN_ID"),
        )

    def _auth_header(self) -> str:
        raw = f"{self._key_id}:{self._key_secret}".encode()
        return "Basic " + base64.b64encode(raw).decode()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
        }
        with httpx.Client(
            base_url=self.API_BASE,
            headers=headers,
            timeout=20.0,
            transport=self._transport,
        ) as client:
            response = client.post(path, json=payload)
            response.raise_for_status()
            value = response.json()
        if not isinstance(value, dict):
            raise RuntimeError("Unexpected Razorpay response.")
        return value

    def create_checkout(
        self,
        *,
        user_id: str,
        sku: str,
        reference_id: str,
        callback_url: str | None = None,
    ) -> CheckoutSession:
        product = get_product(sku)
        if product.kind in {ProductKind.PROJECT, ProductKind.PROJECT_PACK}:
            payload: dict[str, Any] = {
                "amount": product.amount_paise,
                "currency": product.currency,
                "reference_id": reference_id,
                "description": f"AI Vastu Architect — {product.name}",
                "notes": {"user_id": user_id, "sku": sku},
            }
            if callback_url:
                payload["callback_url"] = callback_url
                payload["callback_method"] = "get"
            result = self._post("/payment_links", payload)
            return CheckoutSession(
                sku=sku,
                provider="razorpay",
                provider_reference_id=str(result["id"]),
                checkout_url=str(result["short_url"]),
            )

        if product.kind == ProductKind.SUBSCRIPTION:
            plan_id = (
                self._monthly_plan_id
                if sku == "pro_monthly"
                else self._yearly_plan_id
            )
            if not plan_id:
                raise RazorpayConfigurationError(
                    f"Razorpay plan id is missing for {sku}."
                )
            total_count = 120 if sku == "pro_monthly" else 10
            result = self._post(
                "/subscriptions",
                {
                    "plan_id": plan_id,
                    "total_count": total_count,
                    "quantity": 1,
                    "customer_notify": True,
                    "notes": {"user_id": user_id, "sku": sku},
                },
            )
            checkout_url = result.get("short_url")
            if not checkout_url:
                raise RuntimeError(
                    "Razorpay subscription did not return a checkout URL."
                )
            return CheckoutSession(
                sku=sku,
                provider="razorpay",
                provider_reference_id=str(result["id"]),
                checkout_url=str(checkout_url),
            )

        raise ValueError("The free SKU does not create a checkout.")

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        if not self._webhook_secret:
            raise RazorpayConfigurationError("Razorpay webhook secret is missing.")
        expected = hmac.new(
            self._webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
