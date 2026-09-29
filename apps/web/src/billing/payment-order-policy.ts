import type { PaymentOrderSummary } from "../api/client";

const TERMINAL_PAYMENT_ORDER_STATUSES = new Set<PaymentOrderSummary["status"]>([
  "fulfilled",
  "checkout_failed",
]);

export function isTerminalPaymentOrder(order: PaymentOrderSummary): boolean {
  return TERMINAL_PAYMENT_ORDER_STATUSES.has(order.status);
}

export function canStartFreshCheckoutAfterOrder(
  order: PaymentOrderSummary,
): boolean {
  if (order.checkout_url) return false;
  return order.status === "pending" || order.status === "checkout_unknown";
}
