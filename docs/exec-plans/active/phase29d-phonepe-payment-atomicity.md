# Phase 29D - PhonePe and Payment Atomicity

Status: **PASS_LOCAL on `phase29`; live PhonePe/database/deployment qualification remains outstanding.**

## Scope

- Correct the server-authoritative launch prices to free / INR 399 / INR 3,399 /
  INR 2,499 monthly / INR 24,999 yearly.
- Persist authenticated checkout intent before provider I/O.
- Add an isolated PhonePe Standard Checkout v2 adapter with fixed official
  endpoints and bounded server-side OAuth/HTTP behavior.
- Treat callbacks as authenticated reconciliation triggers; confirm payment
  through PhonePe order status before granting value.
- Apply provider event, monotonic order state, and entitlement in one database
  transaction with replay and concurrency protection.
- Keep PhonePe independent of Razorpay credentials. Retain Razorpay only if its
  selected flow uses the same atomic order binding.
- Reconcile missed or ambiguous callbacks through the same settlement path.

## Non-goals and protected contracts

- PhonePe Standard Checkout must not impersonate recurring AutoPay. Monthly and
  yearly subscription checkout remains fail-closed until a genuine, qualified
  AutoPay lifecycle is implemented.
- Browser redirects and provider metadata never grant entitlement.
- No PlanDocument, geometry, solver, Vastu, revision, generation, or export
  authority changes are permitted.
- Live payment, deployed database isolation, and webhook delivery claims require
  real reviewed credentials and external evidence.

## Workstreams

1. Billing order model, atomic repositories, migration, and pricing regressions.
2. PhonePe HTTP adapter and secret-free provider fixtures.
3. Authenticated checkout/order API, signed webhook trigger, reconciliation,
   production configuration, and launch checks.
4. Fixture engineering followed by independent regression, adversarial,
   security, QA, and release audit.

## Required gates

Focused billing/provider/API/settings/migration tests first; affected auth,
generation, persistence, and production tests next; then Ruff, mypy,
`git diff --check`, and `pnpm validate`. No qualification tag without actual
live PhonePe and deployment evidence.
