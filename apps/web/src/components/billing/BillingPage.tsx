"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import {
  configuredApiBaseUrl,
  ProjectApiClient,
  type PaymentOrderSummary,
} from "../../api/client";
import { browserAccessToken } from "../../auth/browser";
import { billingProductBySku } from "../../billing/catalog";
import {
  canStartFreshCheckoutAfterOrder,
  isTerminalPaymentOrder,
} from "../../billing/payment-order-policy";

const ACTIVE_ORDER_KEY = "vastudraw.billing.active-order";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Payment request failed.";
}

export function BillingPage() {
  const searchParams = useSearchParams();
  const requestedSku = searchParams.get("plan");
  const requested = requestedSku
    ? billingProductBySku(requestedSku)
    : undefined;
  const client = useMemo(
    () =>
      new ProjectApiClient(configuredApiBaseUrl(), fetch, browserAccessToken),
    [],
  );
  const [order, setOrder] = useState<PaymentOrderSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const merchantOrderId = window.sessionStorage.getItem(ACTIVE_ORDER_KEY);
    if (!merchantOrderId) return;
    void client
      .getPaymentOrder(merchantOrderId)
      .then(setOrder)
      .catch((caught: unknown) => {
        setError(errorMessage(caught));
      });
  }, [client]);

  useEffect(() => {
    if (!order || !isTerminalPaymentOrder(order)) return;
    window.sessionStorage.removeItem(
      `vastudraw.billing.idempotency.${order.sku}`,
    );
    if (
      window.sessionStorage.getItem(ACTIVE_ORDER_KEY) ===
      order.merchant_order_id
    ) {
      window.sessionStorage.removeItem(ACTIVE_ORDER_KEY);
    }
  }, [order]);

  async function startCheckoutForSku(sku: string, fresh = false) {
    const product = billingProductBySku(sku);
    if (!product || product.checkoutMode !== "one_time") return;
    setBusy(true);
    setError("");
    const keyName = `vastudraw.billing.idempotency.${sku}`;
    if (fresh) {
      window.sessionStorage.removeItem(keyName);
    }
    const idempotencyKey =
      window.sessionStorage.getItem(keyName) ?? crypto.randomUUID();
    window.sessionStorage.setItem(keyName, idempotencyKey);
    try {
      const nextOrder = await client.createBillingCheckout(sku, idempotencyKey);
      setOrder(nextOrder);
      window.sessionStorage.setItem(
        ACTIVE_ORDER_KEY,
        nextOrder.merchant_order_id,
      );
      if (nextOrder.checkout_url) {
        window.location.assign(nextOrder.checkout_url);
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function refreshOrder() {
    if (!order) return;
    setBusy(true);
    setError("");
    try {
      setOrder(await client.refreshPaymentOrder(order.merchant_order_id));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f7f8f6",
        color: "#172018",
        padding: "48px 28px",
      }}
    >
      <div style={{ maxWidth: "920px", margin: "0 auto" }}>
        <Link href="/pricing" style={{ color: "inherit", fontWeight: 700 }}>
          ← Pricing
        </Link>
        <h1 style={{ fontSize: "44px", letterSpacing: "-0.035em" }}>
          Billing & usage
        </h1>

        {requested ? (
          <section
            style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: "18px",
              padding: "24px",
              marginBottom: "18px",
            }}
          >
            <p style={{ marginTop: 0, color: "#5f6e62", fontWeight: 800 }}>
              SELECTED PLAN
            </p>
            <h2>{requested.name}</h2>
            <p style={{ fontSize: "28px", fontWeight: 800 }}>
              {requested.price}
              {requested.suffix ?? ""}
            </p>
            <p>{requested.description}</p>
            {requested.checkoutMode === "one_time" ? (
              <button
                type="button"
                disabled={busy}
                onClick={() => void startCheckoutForSku(requested.sku)}
                style={{
                  border: 0,
                  borderRadius: "10px",
                  padding: "12px 18px",
                  background: "#285b38",
                  color: "#ffffff",
                  fontWeight: 800,
                  cursor: busy ? "wait" : "pointer",
                }}
              >
                {busy ? "Preparing checkout…" : "Continue to secure payment"}
              </button>
            ) : requested.checkoutMode === "free" ? (
              <Link href="/generation">Start free generation</Link>
            ) : (
              <p role="status">
                Coming soon. Recurring checkout remains disabled until AutoPay
                is qualified.
              </p>
            )}
          </section>
        ) : null}

        {order ? (
          <section
            style={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: "18px",
              padding: "24px",
              marginBottom: "18px",
            }}
          >
            <h2 style={{ marginTop: 0 }}>Payment status</h2>
            <p role="status">
              Server order <code>{order.merchant_order_id}</code>:{" "}
              {order.status}
            </p>
            {!isTerminalPaymentOrder(order) ? (
              <>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void refreshOrder()}
                >
                  {busy ? "Checking…" : "Check payment status"}
                </button>
                {canStartFreshCheckoutAfterOrder(order) ? (
                  <>
                    <p style={{ color: "#606960", lineHeight: 1.6 }}>
                      This attempt has no usable checkout link. You may start a
                      fresh checkout; the earlier server order remains available
                      for safe reconciliation and cannot grant duplicate credit.
                    </p>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void startCheckoutForSku(order.sku, true)}
                    >
                      {busy ? "Preparing…" : "Start a new checkout"}
                    </button>
                  </>
                ) : null}
              </>
            ) : null}
          </section>
        ) : null}

        {error ? (
          <p role="alert" style={{ color: "#9f1d20" }}>
            {error}
          </p>
        ) : null}

        <section
          style={{
            background: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: "18px",
            padding: "24px",
          }}
        >
          <h2 style={{ marginTop: 0 }}>Account entitlement</h2>
          <p style={{ color: "#606960", lineHeight: 1.6 }}>
            Live usage is server-authoritative. When authenticated, this page
            will read <code>/billing/me</code>; checkout is created through
            <code> /billing/checkout</code>. Payment credentials remain on the
            server, and completed orders are reconciled before entitlement is
            granted.
          </p>
          <p style={{ marginBottom: 0 }}>
            One-time project purchases are available through the configured
            gateway. Monthly and yearly checkout stays unavailable until a
            recurring-payment mandate flow is qualified.
          </p>
        </section>
      </div>
    </main>
  );
}
