import hashlib
import hmac

import httpx
import pytest

from ai_vastu.billing.razorpay import RazorpayClient


def test_razorpay_webhook_hmac_verification() -> None:
    body = b'{"event":"payment_link.paid"}'
    secret = "webhook-secret"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    client = RazorpayClient(
        key_id="rzp_test_key",
        key_secret="secret",
        webhook_secret=secret,
    )

    assert client.verify_webhook_signature(body, signature)
    assert not client.verify_webhook_signature(body + b"x", signature)


def test_razorpay_checkout_accepts_only_typed_provider_owned_https_url() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": "plink_123", "short_url": "https://rzp.io/i/checkout"},
        )

    client = RazorpayClient(
        key_id="rzp_test_key",
        key_secret="secret",
        webhook_secret="webhook-secret",
        transport=httpx.MockTransport(handler),
    )

    session = client.create_checkout(
        user_id="user-1",
        sku="project_single",
        reference_id="vd_order_1",
    )

    assert session.provider_reference_id == "plink_123"
    assert session.checkout_url == "https://rzp.io/i/checkout"


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "plink_123", "short_url": "javascript:alert(1)"},
        {"id": "plink_123", "short_url": "https://attacker.example/collect"},
        {"id": {"unexpected": True}, "short_url": "https://rzp.io/i/checkout"},
    ],
)
def test_razorpay_checkout_rejects_untrusted_or_malformed_response(
    payload: dict[str, object],
) -> None:
    client = RazorpayClient(
        key_id="rzp_test_key",
        key_secret="secret",
        webhook_secret="webhook-secret",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, json=payload)
        ),
    )

    with pytest.raises(RuntimeError, match="Unexpected Razorpay response"):
        client.create_checkout(
            user_id="user-1",
            sku="project_single",
            reference_id="vd_order_1",
        )


@pytest.mark.parametrize("status_code", [401, 429, 500, 503])
def test_razorpay_provider_http_failures_are_sanitized(status_code: int) -> None:
    client = RazorpayClient(
        key_id="rzp_test_key",
        key_secret="secret",
        webhook_secret="webhook-secret",
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(status_code, text="provider-secret-body")
        ),
    )

    with pytest.raises(RuntimeError, match=r"^Razorpay request failed\.$"):
        client.create_checkout(
            user_id="user-1",
            sku="project_single",
            reference_id="vd_order_1",
        )


def test_razorpay_timeout_and_oversized_response_fail_safely() -> None:
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("provider-secret-body", request=request)

    for transport in (
        httpx.MockTransport(timeout_handler),
        httpx.MockTransport(
            lambda _request: httpx.Response(200, content=b"x" * (64 * 1024 + 1))
        ),
    ):
        client = RazorpayClient(
            key_id="rzp_test_key",
            key_secret="secret",
            webhook_secret="webhook-secret",
            transport=transport,
        )
        with pytest.raises(RuntimeError):
            client.create_checkout(
                user_id="user-1",
                sku="project_single",
                reference_id="vd_order_1",
            )
