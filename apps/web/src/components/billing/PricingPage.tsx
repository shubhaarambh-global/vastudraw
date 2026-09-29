import Link from "next/link";

import { billingProducts } from "../../billing/catalog";

const cardStyle = {
  border: "1px solid #e5e7eb",
  borderRadius: "18px",
  padding: "24px",
  background: "#ffffff",
} as const;

export function PricingPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f7f8f6",
        color: "#172018",
        padding: "48px 28px 72px",
      }}
    >
      <div style={{ maxWidth: "1180px", margin: "0 auto" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "24px",
          }}
        >
          <div>
            <p style={{ margin: 0, fontSize: "13px", fontWeight: 700 }}>
              AI VASTU ARCHITECT
            </p>
            <h1
              style={{
                margin: "12px 0 10px",
                fontSize: "clamp(36px, 6vw, 64px)",
                lineHeight: 1,
                letterSpacing: "-0.04em",
              }}
            >
              Start free. Pay for real project work.
            </h1>
            <p
              style={{ maxWidth: "720px", fontSize: "18px", color: "#566057" }}
            >
              Project purchases are project entitlements, not generation
              counters. Regenerate and refine a paid project without buying it
              again.
            </p>
          </div>
          <Link href="/" style={{ color: "inherit", fontWeight: 700 }}>
            Back to app
          </Link>
        </div>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
            gap: "16px",
            marginTop: "40px",
          }}
        >
          {billingProducts.map((product) => (
            <article
              key={product.sku}
              style={{
                ...cardStyle,
                outline: product.featured ? "2px solid #285b38" : "none",
              }}
            >
              <div
                style={{
                  fontSize: "12px",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  color: "#5f6e62",
                }}
              >
                {product.eyebrow}
              </div>
              <h2 style={{ marginBottom: "8px" }}>{product.name}</h2>
              <div style={{ fontSize: "32px", fontWeight: 800 }}>
                {product.price}
                {product.suffix ? (
                  <span style={{ fontSize: "14px", fontWeight: 600 }}>
                    {product.suffix}
                  </span>
                ) : null}
              </div>
              <p
                style={{
                  minHeight: "72px",
                  color: "#606960",
                  lineHeight: 1.55,
                }}
              >
                {product.description}
              </p>
              {product.checkoutMode === "coming_soon" ? (
                <span
                  role="status"
                  style={{
                    display: "inline-block",
                    marginTop: "8px",
                    borderRadius: "10px",
                    padding: "11px 15px",
                    background: "#eef1ed",
                    color: "#566057",
                    fontWeight: 800,
                  }}
                >
                  Coming soon · AutoPay qualification pending
                </span>
              ) : (
                <Link
                  href={`/billing?plan=${product.sku}`}
                  style={{
                    display: "inline-block",
                    marginTop: "8px",
                    borderRadius: "10px",
                    padding: "11px 15px",
                    textDecoration: "none",
                    background: product.featured ? "#285b38" : "#eef1ed",
                    color: product.featured ? "#ffffff" : "#172018",
                    fontWeight: 800,
                  }}
                >
                  {product.checkoutMode === "free"
                    ? "Start free"
                    : "Choose plan"}
                </Link>
              )}
            </article>
          ))}
        </section>

        <section style={{ ...cardStyle, marginTop: "20px" }}>
          <strong>Billing rules</strong>
          <p style={{ marginBottom: 0, color: "#606960", lineHeight: 1.6 }}>
            The first successful generation is free once per account. A failed
            generation does not consume it. Single-project and 10-project
            purchases grant permanent project entitlements. Monthly and yearly
            prices are published for the planned AutoPay launch, but recurring
            checkout remains unavailable until that flow is qualified.
          </p>
        </section>
      </div>
    </main>
  );
}
