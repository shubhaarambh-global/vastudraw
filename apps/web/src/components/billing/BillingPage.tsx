"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { billingProducts } from "../../billing/catalog";

export function BillingPage() {
  const searchParams = useSearchParams();
  const requestedSku = searchParams.get("plan");
  const requested = billingProducts.find((item) => item.sku === requestedSku);

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
          </section>
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
            <code> /billing/checkout</code>. Razorpay keys are never exposed to
            the browser.
          </p>
          <p style={{ marginBottom: 0 }}>
            Phase 23 intentionally keeps entitlement decisions on the API even
            though the pricing cards are rendered in the web app.
          </p>
        </section>
      </div>
    </main>
  );
}
