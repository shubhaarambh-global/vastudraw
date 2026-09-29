from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import re
from typing import Any, NoReturn
from urllib.parse import urlparse

import httpx

from .catalog import ProductKind, get_product
from .models import CheckoutSession


class RazorpayConfigurationError(RuntimeError):
    pass


_PROVIDER_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_MAX_RESPONSE_BYTES = 64 * 1024


def _decode_response(body: bytes) -> dict[str, Any]:
    def reject_constant(_value: str) -> NoReturn:
        raise ValueError

    def parse_finite_float(raw_value: str) -> float:
        result = float(raw_value)
        if not math.isfinite(result):
            raise ValueError
        return result

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    try:
        value = json.loads(
            body,
            parse_constant=reject_constant,
            parse_float=parse_finite_float,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise RuntimeError("Unexpected Razorpay response.") from None
    if not isinstance(value, dict):
        raise RuntimeError("Unexpected Razorpay response.")
    return value


def _checkout_session(sku: str, result: dict[str, Any]) -> CheckoutSession:
    provider_id = result.get("id")
    checkout_url = result.get("short_url")
    if (
        not isinstance(provider_id, str)
        or _PROVIDER_ID_PATTERN.fullmatch(provider_id) is None
        or not isinstance(checkout_url, str)
        or len(checkout_url) > 2048
    ):
        raise RuntimeError("Unexpected Razorpay response.")
    parsed = urlparse(checkout_url)
    hostname = parsed.hostname or ""
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.port not in {None, 443}
        or not (hostname == "rzp.io" or hostname.endswith(".razorpay.com"))
    ):
        raise RuntimeError("Unexpected Razorpay response.")
    return CheckoutSession(
        sku=sku,
        provider="razorpay",
        provider_reference_id=provider_id,
        checkout_url=checkout_url,
    )


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
        try:
            with httpx.Client(
                base_url=self.API_BASE,
                headers=headers,
                timeout=20.0,
                transport=self._transport,
            ) as client, client.stream("POST", path, json=payload) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    raise RuntimeError("Razorpay request failed.")
                raw_length = response.headers.get("Content-Length")
                if raw_length is not None:
                    try:
                        declared_length = int(raw_length)
                    except ValueError:
                        raise RuntimeError("Unexpected Razorpay response.") from None
                    if declared_length < 0 or declared_length > _MAX_RESPONSE_BYTES:
                        raise RuntimeError("Unexpected Razorpay response.")
                body = bytearray()
                for chunk in response.iter_bytes():
                    if len(body) + len(chunk) > _MAX_RESPONSE_BYTES:
                        raise RuntimeError("Unexpected Razorpay response.")
                    body.extend(chunk)
        except RuntimeError:
            raise
        except (httpx.RequestError, httpx.TimeoutException):
            raise RuntimeError("Razorpay request failed.") from None
        return _decode_response(bytes(body))

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
            return _checkout_session(sku, result)

        if product.kind == ProductKind.SUBSCRIPTION:
            plan_id = self._monthly_plan_id if sku == "pro_monthly" else self._yearly_plan_id
            if not plan_id:
                raise RazorpayConfigurationError(f"Razorpay plan id is missing for {sku}.")
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
            return _checkout_session(sku, result)

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
