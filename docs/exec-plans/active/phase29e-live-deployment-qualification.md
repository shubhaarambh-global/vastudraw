# Phase 29E - Live / Deployment End-to-End Qualification

Status: **LOCAL DEVELOPMENT E2E PASS; LIVE EXTERNAL GATES BLOCKED**

## Qualification boundary

- Phase 29D has a reviewed `PASS_LOCAL` tree, but the required checkpoint commit
  is `BLOCKED_HUMAN_ACTION` because the managed session cannot write `.git` and
  therefore cannot create `index.lock`.
- No production-qualified tag is permitted.
- Current payment policy is fixed at `APP_ENV=development` with PhonePe and
  Razorpay disabled. No payment credentials, provider calls, callbacks,
  webhooks, sandbox flows, or real-money transactions are permitted. Live
  payment qualification is deliberately `BLOCKED_HUMAN_ACTION` until the user
  explicitly enables it; this is expected and is not a Phase 29E failure.
- The current process contains no production database, Supabase, NVIDIA NIM,
  PhonePe, deployment, or active-provider configuration.
- The repository-local, Git-ignored `.env.production` is a legacy pre-Phase-29 profile. It
  uses superseded database/origin/provider keys, selects `openai`, and lacks the
  current storage, payment, PhonePe, NVIDIA NIM, and active-provider
  contract. It must not be loaded, copied, or used to select a live target.
- No external call, production write, migration, payment, backup, restore, or
  deployment action was performed during this preparation.

## Evidence labels

Every external gate uses exactly one of:

- `PASS_LOCAL`
- `PASS_LIVE`
- `BLOCKED_CREDENTIALS`
- `BLOCKED_HUMAN_ACTION`
- `BLOCKED_EXTERNAL_SERVICE`
- `FAIL`

Local fixtures and configuration checks never count as `PASS_LIVE`.

## Current gate ledger

| Gate | Status | Current evidence / blocker |
| --- | --- | --- |
| Phase 29D local implementation and regression surface | `PASS_LOCAL` | Preserved GREEN checkpoint: 940 Python, 32 web, Ruff, mypy across 208 files, formatting/lint/typecheck/build, Phase 29C gate, and Phase 29D gate passed. |
| Phase 29D checkpoint commit | `BLOCKED_HUMAN_ACTION` | Managed `.git` is read-only; exact selective `git add` failed because Git could not create `.git/index.lock`. |
| PostgreSQL connectivity and TLS | `BLOCKED_CREDENTIALS` | No current database URL is loaded and no reviewed staging target is identified. |
| PostgreSQL repository/migration policy checks (not runtime qualification) | `PASS_LOCAL` | Static repository and migration-policy tests passed; PostgreSQL execution, grants, RLS, and deployed metadata remain uninspected. |
| Live ownership denial and revision persistence | `BLOCKED_CREDENTIALS` | Requires an approved isolated staging database and two test identities. |
| Backup safety logic and deterministic stub artifacts (not a backup/restore drill) | `PASS_LOCAL` | Offline backup policy and artifact-scope tests passed; no PostgreSQL dump or restore was executed. |
| Real PostgreSQL backup creation | `BLOCKED_CREDENTIALS` | No approved database/storage target, PostgreSQL tools, or backup destination is configured. |
| Disposable restore drill | `BLOCKED_HUMAN_ACTION` | Requires an explicitly authorized new disposable restore database and retention/cleanup decision. |
| Fixture JWT issuer, audience, expiry, signature, algorithm, and ownership denial | `PASS_LOCAL` | Signed fixture and API ownership matrices passed; live Supabase remains credential-blocked. |
| Deployed CORS and rate limits | `BLOCKED_HUMAN_ACTION` | No reviewed deployment URL, edge/proxy identity, or authorized rate-test window is supplied. |
| NVIDIA NIM adapter/error/redaction fixture contract | `PASS_LOCAL` | Deterministic HTTP fixtures, local PDF rendering, and provider isolation passed without an external call; provider runtime is not qualified. |
| NVIDIA model inventory + text + JPG/PNG/PDF live check | `BLOCKED_CREDENTIALS` | `NVIDIA_API_KEY` and an NVIDIA-only qualification process are required. Inventory must verify the active Ultra and Nano Omni pins before any completion request. |
| NVIDIA production entitlement | `BLOCKED_HUMAN_ACTION` | Hosted development/staging success does not establish production entitlement, quota, support, or data-handling terms. |
| AI deterministic-authority boundary | `PASS_LOCAL` | Existing qualified local gates keep AI advisory and deterministic geometry/validators authoritative. |
| PhonePe live/sandbox qualification | `BLOCKED_HUMAN_ACTION` | Explicitly deferred by development policy; no credentials or provider access may be requested or used. |
| Razorpay live/sandbox qualification | `BLOCKED_HUMAN_ACTION` | Explicitly deferred by development policy; provider remains implemented but disabled. |
| Payment replay/duplicate/exactly-once fixture behavior | `PASS_LOCAL` | Phase 29D local fixture, adversarial, repository, and API evidence passed; genuine sandbox delivery remains blocked. |
| Fixture-backed development workflow E2E | `PASS_LOCAL` | Development auth, project, JPG/PNG/PDF intake, fixture AI, human confirmation, real deterministic candidate generation/validation/Vastu, selection, SQLite persistence, reload, revision, PDF export, and explicit billing bypass passed with payment-provider tripwires. This is not a deployed, PostgreSQL, Supabase, or live-provider E2E. |
| Deployed production-equivalent end-to-end workflow | `BLOCKED_CREDENTIALS` | No database, Supabase, NVIDIA NIM, or deployment credentials are loaded; payment remains separately deferred by human policy. |

## Local development qualification evidence

- Added `apps/api/tests/test_phase29e_development_e2e.py` with PhonePe and
  Razorpay method tripwires. It passed with both providers disabled and no
  provider credentials present.
- The workflow exercised project creation; JPG, PNG, and PDF intake; fixture
  plan recognition; explicit human geometry confirmation; fixture requirements
  interpretation; confirmed program; real deterministic candidate generation;
  hard validation and Vastu scoring; selection; immutable persistence/reload;
  a second revision; PDF export; and development-bypass entitlement.
- The workflow exposed and corrected a JSON-boundary defect in the candidate
  selection route. Valid serialized canonical UUID/enum/tuple fields are now
  parsed through `PlanDocument.model_validate_json`, matching the existing
  revision API boundary. Canonical schema and geometry authority did not change.
- Focused E2E file: **2 passed** (the complete workflow plus malformed-selection
  rejection before billing/provider access).
- Auth/JWT, ownership, persistence, uploads, exports, provider-runtime,
  production-settings, rate-limit, backup-safeguard, and project-policy matrix:
  **224 passed**.
- Additional database-policy and hybrid provider-fixture matrix: **29 passed**.
- Ruff on the two Phase 29E files: **PASS**.
- mypy on the two Phase 29E files: **PASS**.
- No Phase 29A-29D broad gate was rerun.
- No PostgreSQL/Supabase/NVIDIA-NIM/payment/deployment external service
  was contacted. No `PASS_LIVE` claim is made.
- Independent QA, architecture, and release review accepted the scoped local
  evidence and rejected any production-qualified or release-ready claim.

## Sequential live procedure

1. Restore `.git` write access, selectively stage the reviewed Phase 29D
   allowlist, inspect cached name/status, stat, check, and complete diff, create
   a normal checkpoint commit, and record its hash. Do not tag.
2. Identify the exact isolated staging deployment, database, Supabase project,
   AI provider accounts, and rollback owner. Print only sanitized identity and
   credential-presence evidence. Payment accounts and callback URLs remain out
   of scope under the current policy.
3. Inspect PostgreSQL connectivity, verified TLS, server/database/application
   role identity, grants, ownership, migration head, RLS enablement/force state,
   and policies read-only. Do not apply migrations to production.
4. On explicitly approved isolated staging only, use two test identities to
   exercise ownership denial, revision persistence/ancestry, reload, and cleanup.
5. Verify Supabase/JWT signature algorithm, exact issuer and audience, expiry/
   not-before, JWKS rotation behavior, malformed-token denial, cross-owner
   denial, deployed CORS, and conservative deployed rate limits.
6. In an NVIDIA-only child process with all six provider switches set to
   `nvidia_nim` and legacy provider credentials removed, authenticate to the
   fixed NVIDIA host and inventory the two active exact model IDs before any
   completion call. Then exercise the sole Ultra text primary, JPG, PNG, and
   locally rendered PDF-path fixture. Verify bounded input,
   MIME/content validation, timeouts, sanitized failures, human confirmation,
   and continued deterministic geometry authority. Keep production entitlement
   `BLOCKED_HUMAN_ACTION` after any hosted development/staging pass.
7. Keep PhonePe and Razorpay disabled. Payment live/sandbox work remains deferred
   until the user explicitly changes the development payment policy.
8. Create a backup from approved staging, then restore only into a newly created
   disposable database. Verify schema, ownership isolation, revision ancestry,
   representative hashes, file manifests, and cleanup/retention evidence.
9. Exercise the non-payment deployed flow with dedicated test identities:
   auth -> project -> requirements -> optional JPG/PNG/PDF upload -> AI
   interpretation -> human confirmation -> candidate generation -> deterministic
   validation -> Vastu evaluation -> selection -> persistence -> reload ->
   revision -> export. The explicitly enabled development billing bypass is
   qualified only by the local development workflow; it must not be enabled in
   staging or production. Deployed payment remains a separate deferred gate.
10. Run independent DB/Auth, AI, payment, backup/restore, E2E, adversarial,
    security, QA, and release reviews. A production tag remains forbidden while
    any required live gate is blocked or failed.

## Required human actions

1. Run Codex in a workspace where `.git` is writable, or perform the exact
   reviewed selective Phase 29D stage/commit and provide the resulting hash.
2. Identify and authorize an isolated staging deployment and disposable restore
   target. Provide deployment/database/Supabase/NVIDIA credentials
   through the approved secret mechanism, never chat or a tracked file. Do not
   provide payment credentials under the current development policy.
3. Provide or authorize two dedicated Supabase test users and any required
   OTP/MFA/CAPTCHA completion.
4. Authorize the staging mutation, conservative rate-limit test window, backup,
   and disposable restore drill. No production write or real-money transaction
   is implied.

## Stop conditions

Stop and classify `FAIL` for disabled TLS verification, excessive database
grants, cross-tenant access, migration drift that cannot be explained, dev
billing bypass in production, secret leakage, AI authority inversion, unsigned
payment acceptance, entitlement before authoritative success, or duplicate
entitlement. Classify a genuine provider outage with otherwise reviewed valid
configuration as `BLOCKED_EXTERNAL_SERVICE`.
