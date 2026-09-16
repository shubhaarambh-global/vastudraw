# Phase 23 — Pricing, Billing, and Entitlements

Phase 23 adds the commercial control plane without changing canonical geometry,
the deterministic CP-SAT planner, or the frozen Vastu rule bundle.

## Canonical INR catalog

- First successful generation: free once per authenticated user.
- Single project: ₹399.
- 10-project pack: ₹3,399.
- Pro Monthly: ₹2,499/month.
- Pro Yearly: ₹24,999/year.

All server amounts are stored in paise.

## Entitlement semantics

A project purchase is a project entitlement, not a generation counter.

- The first free project may perform one successful generation.
- Failed/rejected generation attempts must not consume the free entitlement.
- A ₹399 entitlement claims one permanent paid project.
- A ₹3,399 pack claims up to ten permanent paid projects.
- Regeneration/editing within a paid project does not consume another project credit.
- Active subscriptions authorize project generation while the subscription is active.
- Subscription cancellation never deletes project data.
- Frontend state is never authoritative for billing.
- Authenticated billing endpoints register project entitlements, authorize generation, and commit successful-generation consumption.

## Payment provider

Razorpay is isolated behind `RazorpayClient`.

- one-time SKUs use Payment Links;
- subscription SKUs use Razorpay Subscriptions;
- webhook signatures use HMAC-SHA256 over the raw request body;
- webhook effects are idempotent;
- production checkout fails closed when provider configuration is absent.

No live charge is made by tests.

## Production configuration

Required for live checkout:

- `AI_VASTU_RAZORPAY_KEY_ID`
- `AI_VASTU_RAZORPAY_KEY_SECRET`
- `AI_VASTU_RAZORPAY_WEBHOOK_SECRET`
- `AI_VASTU_RAZORPAY_MONTHLY_PLAN_ID`
- `AI_VASTU_RAZORPAY_YEARLY_PLAN_ID`

Production billing persistence uses `AI_VASTU_DATABASE_URL`.
Development uses `AI_VASTU_BILLING_SQLITE_PATH` or `.local/billing.sqlite3`.

Phase 23 does not alter the frozen Vastu production hashes.

## Phase 24 binding boundary

The historical Phase 16 deterministic generation endpoint predates project-bound billing and
is intentionally not mutated in Phase 23. The final project-bound multimodal workflow in
Phase 24 must call:

- `POST /billing/projects/{project_id}/register`
- `GET /billing/projects/{project_id}/generation-authorization`
- `POST /billing/projects/{project_id}/generation-succeeded`

before/after final generation. This avoids pretending a legacy engineering endpoint is a
commercial checkout surface.
