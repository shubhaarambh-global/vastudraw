# Phase 29C - Hybrid AI Production Integration

Status: local implementation and validation complete; live qualification blocked by credentials

Baseline commits:

- Phase 29A/29B implementation: `abb24feb0209a18f14877c2f8154e24c4dbcffcc`
- Phase 29A/29B checkpoint metadata: `a6f59747d00facf2b6387e31a7e4e670ef215ef9`

## Model routing

Per the user policy, all Phase 29C agents use GPT-5.6 Sol. Mechanical work uses
medium effort; planning, implementation, debugging, architecture, security,
testing, QA and release review use high effort. Escalation remains within
GPT-5.6 Sol unless it is unavailable or two evidence-backed attempts fail.

## Accepted scope

1. Preserve explicit provider responsibilities and existing role factories:
   OpenRouter for text/reasoning roles and direct Gemini for the dedicated
   existing-plan recognition route.
2. Add a small shared provider runtime contract with typed, sanitized failure
   categories and bounded attempt/total budgets.
3. OpenRouter may try the pinned primary once and the existing approved free
   fallback once. Non-retryable client/auth failures fail immediately. No
   random, paid, unpinned or cross-provider fallback is allowed.
4. Direct Gemini retries only bounded transient statuses/transport failures and
   never switches model or provider. Successful malformed/schema-invalid output
   is not retried.
5. Map provider configuration/auth/unavailable/timeout/invalid-response failures
   to fixed sanitized API responses; never expose raw provider bodies, prompts,
   file bytes, secrets or authorization headers.
6. Run synchronous requirements provider work in the FastAPI threadpool after
   async upload reads.
7. Preserve deterministic candidate rejection as `422`, while Architectural
   Brain provider outages surface as upstream failures.
8. Force direct-Gemini image/PDF observations to remain non-authoritative,
   non-`USER_CONFIRMED`, and confirmation-required.
9. Add a POST-only production rate-limit scope for plan analysis. Correct
   middleware ordering so limiter/config error responses receive the existing
   CORS policy; do not broaden the Phase 29E smoke scope otherwise.
10. Correct Phase 27/28 live-check wiring and add explicit offline/live Phase
    29C evidence without running live services unless credentials are present
    and the target is safe.
11. Treat provider responses and uploaded plans as bounded untrusted input:
    stream provider bodies under a 2 MiB cap and total deadline, verify image
    content through the explicit Pillow adapter, reject MIME/extension mismatch,
    and screen PDFs for header/terminal-EOF truncation before provider use.
12. Fail closed on unknown `APP_ENV`, key outer provider-abuse limits by client
    IP rather than bearer-token text, and document exact proxy trust/retention
    requirements.

## Deferred product decision

The existing `/requirements/interpret` compatibility path can send visual
requirements evidence to the pinned OpenRouter vision model. It is distinct
from the persisted Analyze Plan route, which uses direct Gemini, but the Phase
28 documentation overstated this distinction. Phase 29C will document actual
runtime behavior and retain the compatibility model. It will not introduce a
new two-provider composite, remove visual requirements, change the persisted
requirements schema, or claim the visual-routing question fully reconciled.

## Protected invariants and non-goals

- AI remains advisory and cannot author canonical geometry.
- Confirmed requirements, deterministic CP-SAT geometry, deterministic
  validators, frozen Vastu, candidate hashes, and Canonical PlanDocument remain
  authoritative.
- No solver, geometry, Vastu rule/hash, PlanDocument, revision persistence,
  billing/payment, database migration, renderer or export semantic change.
- No global provider switch or duplicate provider factory.
- No live database/storage launch probe, provider call, account action, tag or
  production qualification during implementation.

## Work ownership

- Transport worker: shared provider runtime, OpenRouter/Gemini HTTP behavior,
  and transport-focused tests only.
- API/provider worker: role-specific provider error translation, advisory
  normalization, API mappings/threadpool behavior, Architectural Brain outage
  routing, and focused tests only.
- Configuration/operations worker: production provider budgets, plan-analysis
  limiter and CORS ordering, environment/docs/live-check scripts, package
  commands, and production-policy tests only.
- Fixture Engineer: separate new Phase 29C fixture files after implementation.
- Coordinator: integration, fix loop, Git, handoff, memory and release claims.

## Required evidence

- OpenRouter fail-fast and approved-fallback matrix;
- Gemini transient retry/no-retry/deadline matrix for JPG, PNG and PDF;
- sanitized `502`/`503`/`504` API behavior with no provider side effects;
- provider routing/factory isolation and no unauthorized fallback;
- advisory/confirmation normalization against malicious provider output;
- POST-only plan-analysis limiter plus CORS on limiter/config errors;
- corrected offline/live checker policy;
- independent regression, adversarial, security and QA reviews;
- focused tests, affected suites, Ruff, mypy, `git diff --check`, and
  `pnpm validate`.

## Definition of done

Local Phase 29C is complete when all accepted-scope evidence is green, protected
paths remain unchanged, live OpenRouter and Gemini status is reported separately
as `PASS_LIVE`, `FAIL`, or `BLOCKED_CREDENTIALS`, and no production qualification
or tag is claimed. The visual-requirements decision remains an explicit launch
blocker unless separately resolved.

## Final local evidence

- `pnpm validate`: PASS on 2026-09-27.
- Ruff: PASS; mypy: PASS across 206 source files.
- Python: 830 passed; web: 26 passed; contracts: 1 passed.
- Next.js production build: PASS.
- Independent Regression, Adversarial, Security, and QA reviews: local ACCEPT
  after their fix loops; no unresolved BLOCKER/HIGH findings.
- OpenRouter live status: `BLOCKED_CREDENTIALS`.
- Gemini live status: `BLOCKED_CREDENTIALS`.
- No production qualification or tag is justified.
