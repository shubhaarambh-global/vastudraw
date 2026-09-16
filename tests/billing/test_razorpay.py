import hashlib
import hmac

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
