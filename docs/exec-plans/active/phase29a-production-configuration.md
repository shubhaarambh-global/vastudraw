# Phase 29A — Production Configuration Contract

Status: implementation and local validation complete; production launch remains blocked by later phases

Baseline: `post-v1-development-qualified` / `cbd295f5e9028186acbfb14f40c1142e3a003b27`

## Scope

- make production authentication configuration agree with the Supabase verifier;
- use `AI_VASTU_DATABASE_URL` consistently for production PostgreSQL consumers;
- make validated CORS origins and trusted hosts govern the API runtime;
- validate the qualified OpenRouter text/reasoning plus direct Gemini plan-vision profile;
- require absolute durable requirements and generation-upload roots;
- reject development authentication and billing bypass in production;
- select a payment gateway explicitly, require Razorpay credentials only when Razorpay is selected, and fail closed before any provider call when PhonePe is selected but not yet implemented;
- update production examples, launch checks, runbook, tests and handoff evidence.

## Non-goals

- PhonePe checkout, status polling or webhook implementation (Phase 29D);
- entitlement transaction redesign, ownership redesign or billing UI changes;
- auth/persistence expansion (Phase 29B) or provider implementation changes (Phase 29C);
- schema or data migrations;
- production deployment or live provider/payment qualification;
- any solver, Vastu, geometry, circulation, canonical PlanDocument or revision-semantics change.

## Protected invariants

- deterministic geometry and validators remain authoritative;
- AI output remains advisory and the qualified runtime split is represented accurately;
- frozen Vastu hashes and semantics remain unchanged;
- canonical units remain integer millimetres;
- project revisions remain immutable and ownership-isolated;
- entitlements remain server-authoritative;
- secrets remain server-side and development bypasses cannot operate in production.

## Work ownership

- Configuration worker: `python/ai_vastu/production/settings.py` and `tests/production/test_*.py` configuration files only.
- API worker: `apps/api/app/main.py`, `apps/api/app/billing_routes.py`, and new API configuration/gateway tests only.
- Coordinator: examples, launch checker, runbook, policy checks, integration, handoff and Git.
- Fixture Engineer: separate fixture/test files after implementation, before broad QA.

## Validation

1. focused production settings and API runtime tests;
2. auth, billing, provider, upload and persistence regression suites;
3. Fixture Engineer cases, then independent Regression and Adversarial tests;
4. Security Reviewer and independent QA challenge;
5. Ruff, mypy, `git diff --check`, then `pnpm validate`;
6. Release Auditor evidence review. No qualification tag in Phase 29A.

Live database, Supabase, OpenRouter, Gemini and payment checks require reviewed credentials/accounts and must be reported as credentials-blocked unless actually exercised.
