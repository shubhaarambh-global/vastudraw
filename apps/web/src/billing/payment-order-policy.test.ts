import assert from "node:assert/strict";
import test from "node:test";

import type { PaymentOrderSummary } from "../api/client";
import {
  canStartFreshCheckoutAfterOrder,
  isTerminalPaymentOrder,
} from "./payment-order-policy.ts";

function order(
  status: PaymentOrderSummary["status"],
  checkoutUrl: string | null = null,
): PaymentOrderSummary {
  return {
    merchant_order_id: "vd-order-1",
    sku: "project_single",
    provider: "phonepe",
    provider_reference_id: null,
    checkout_url: checkoutUrl,
    status,
    amount_paise: 39_900,
    currency: "INR",
  };
}

void test("only terminal payment states are treated as terminal", () => {
  assert.equal(isTerminalPaymentOrder(order("fulfilled")), true);
  assert.equal(isTerminalPaymentOrder(order("checkout_failed")), true);
  assert.equal(isTerminalPaymentOrder(order("pending")), false);
  assert.equal(isTerminalPaymentOrder(order("checkout_created")), false);
  assert.equal(isTerminalPaymentOrder(order("checkout_unknown")), false);
});

void test("fresh checkout is offered only when a recoverable order has no redirect", () => {
  assert.equal(canStartFreshCheckoutAfterOrder(order("pending")), true);
  assert.equal(
    canStartFreshCheckoutAfterOrder(order("checkout_unknown")),
    true,
  );
  assert.equal(
    canStartFreshCheckoutAfterOrder(
      order("checkout_created", "https://mercury-uat.phonepe.com/pay/token"),
    ),
    false,
  );
  assert.equal(canStartFreshCheckoutAfterOrder(order("fulfilled")), false);
  assert.equal(
    canStartFreshCheckoutAfterOrder(order("checkout_failed")),
    false,
  );
});
