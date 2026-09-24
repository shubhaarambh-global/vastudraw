# Phase 29B — Auth and Persistence Hardening

Status: implemented and locally validated; not production-qualified

Baseline: Phase 29A locally validated working tree on `phase29` at
`cbd295f5e9028186acbfb14f40c1142e3a003b27`.

## Scope

- route every user-facing API request through the canonical verifier stored in
  `request.app.state.access_token_verifier`;
- require canonical token claims consistently across project, billing,
  requirements and confirmed-generation routes;
- enforce current project ownership before requirements provider/storage work
  and billing project-entitlement reads or mutations;
- retain non-disclosing 404 behavior for foreign or missing projects;
- replace requirements JSON using unique same-directory temporary files and
  atomic replacement while preserving existing reconfirmation behavior;
- require an explicit absolute generation-upload root in staging as well as
  production;
- update production backup coverage to use `AI_VASTU_DATABASE_URL` and archive
  both requirements and generation-upload roots;
- use the existing Supabase transaction-pooler compatibility option for the
  billing PostgreSQL pool.

## Non-goals

- SQL/RLS/grant migrations or production database changes;
- billing event/entitlement transaction redesign or payment reconciliation;
- PhonePe implementation;
- billing connection-pool lifecycle redesign;
- provider runtime changes, middleware error ordering, canonical schema,
  project revision semantics, solver, geometry or Vastu behavior;
- live database, Supabase, backup, provider or payment execution.

## Protected invariants

- project ownership remains server enforced and cross-tenant resources remain
  concealed;
- canonical revisions remain immutable and ancestry aware;
- requirements reconfirmation retains its existing replace semantics;
- production and staging cannot silently fall back to SQLite or local upload
  roots;
- secrets remain server-side and development auth remains unavailable in
  production/staging;
- deterministic geometry, frozen Vastu and Canonical PlanDocument behavior are
  untouched.

## Work ownership

- API worker: `apps/api/app/auth_dependencies.py`, `apps/api/app/main.py`,
  `apps/api/app/billing_routes.py`, `apps/api/app/requirements_routes.py`,
  `apps/api/app/confirmed_generation_routes.py`,
  `apps/api/tests/test_phase29b_auth.py`, and the Phase 29A runtime test
  compatibility update only.
- Persistence worker: `python/ai_vastu/requirements/store.py`,
  `python/ai_vastu/generation_intake/store.py`,
  `python/ai_vastu/billing/postgres_repository.py`,
  `scripts/backup-production.ps1`, `docs/runbooks/backup-restore.md`, and
  their explicitly named persistence/backup tests only.
- Fixture Engineer: separate new fixture/test files after implementation and
  before broad QA.
- Coordinator: integration, plan/handoff/memory, Git and release claims.

## Required evidence

1. offline signed-token claim matrix and injected-verifier behavior across all
   route families;
2. foreign/missing project requests return concealed 404 before provider,
   storage or entitlement side effects;
3. atomic write, reconfirmation, failure-retains-old-data and cleanup tests;
4. production/staging upload configuration fixtures;
5. offline backup-policy tests and billing pool configuration test;
6. focused tests, affected subsystem suites, Ruff, mypy and
   `git diff --check`;
7. independent regression, adversarial, security and QA reviews;
8. `pnpm validate` and Release Auditor review.

Local validation does not qualify database grants, deployed storage, backups or
live Supabase behavior. Missing billing-table RLS/revokes remains an explicit
deployment blocker for a separately reviewed migration.

## Closure evidence

- Fixture Engineer: 11 offline signed-token and injected-verifier fixtures passed.
- Regression Tester: 52 focused tests and 257 affected-subsystem tests passed;
  Ruff, mypy across 40 source files, and `git diff --check` passed.
- Adversarial Tester: 56 focused tests passed; malformed expiry and backup path
  bypass findings were fixed and retested.
- Security Reviewer: local Phase 29B security accepted after the backup fixes;
  effective database grants/RLS/TLS and Phase 29D payment atomicity remain
  deployment blockers.
- Independent QA: local implementation accepted after 52 focused tests and 32
  additional signed-token route probes.
- Coordinator `pnpm validate`: passed with Ruff, mypy across 200 source files,
  643 Python tests, 26 web tests, one contract test, production build, and all
  deterministic phase checks.
- Release Auditor accepted the uncommitted local handoff wording and blocked
  any qualification tag because live/deployment evidence is absent and current
  HEAD does not contain the Phase 29A/B working-tree changes.
- No live service, migration, deployment, staging, commit, or tag was performed.
