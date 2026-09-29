from __future__ import annotations

import argparse
import json
import os

from ai_vastu.billing import (
    BillingService,
    PaymentOrderConflictError,
    PhonePeOrderState,
    create_billing_repository,
)
from ai_vastu.billing.phonepe import PhonePeProviderError
from ai_vastu.billing.phonepe_factory import create_phonepe_client


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile pending PhonePe payment orders.")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    limit = min(max(args.limit, 1), 500)

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in {"development", "production"}:
        print(json.dumps({"error": "invalid_app_environment"}, sort_keys=True))
        return 2

    repository = create_billing_repository()
    service = BillingService(repository)
    counts = {"checked": 0, "fulfilled": 0, "failed": 0, "pending": 0, "errors": 0}
    try:
        orders = service.list_reconcilable_payment_orders("phonepe", limit)
        with create_phonepe_client() as client:
            for order in orders:
                counts["checked"] += 1
                try:
                    status = client.get_order_status(order.merchant_order_id)
                    currency = status.currency or order.currency
                    if status.amount_paise != order.amount_paise or currency != order.currency:
                        counts["errors"] += 1
                        continue
                    if status.state == PhonePeOrderState.COMPLETED:
                        changed = service.apply_payment_order_event(
                            provider="phonepe",
                            event_key=f"{order.merchant_order_id}:completed",
                            event_type="reconciliation",
                            merchant_order_id=order.merchant_order_id,
                            provider_order_id=status.provider_order_id,
                            amount_paise=status.amount_paise,
                            currency=currency,
                        )
                        counts["fulfilled"] += int(changed)
                    elif status.state == PhonePeOrderState.FAILED:
                        service.mark_checkout_failed(
                            provider="phonepe",
                            merchant_order_id=order.merchant_order_id,
                            failure_code="provider_failed",
                        )
                        counts["failed"] += 1
                    else:
                        counts["pending"] += 1
                except (PaymentOrderConflictError, PhonePeProviderError):
                    counts["errors"] += 1
    finally:
        repository.close()

    print(json.dumps(counts, sort_keys=True))
    return 1 if counts["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
