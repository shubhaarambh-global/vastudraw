import { Suspense } from "react";

import { BillingPage } from "../../components/billing/BillingPage";

export default function BillingRoute() {
  return (
    <Suspense
      fallback={<main style={{ padding: "32px" }}>Loading billing…</main>}
    >
      <BillingPage />
    </Suspense>
  );
}
