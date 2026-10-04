# Phase 29E Non-Payment Staging Setup

Status: **SETUP PREPARED; LIVE QUALIFICATION BLOCKED**

## Scope and evidence boundary

This plan qualifies only the non-payment Phase 29E staging surface. No external
call is authorized until the staging target, credentials, identities, mutation
window, evidence location, and cleanup owner have been supplied and reviewed.

Current gate state:

| Gate | Status | Reason |
| --- | --- | --- |
| Local development workflow | `PASS_LOCAL` | Fixture-backed Phase 29E workflow passed locally. |
| PostgreSQL/Supabase, auth, and separately configured NVIDIA hosted staging | `BLOCKED_CREDENTIALS` | No reviewed staging target or credentials are loaded. |
| Staging mutation, deployment, and restore | `BLOCKED_HUMAN_ACTION` | Target selection and explicit operator authorization are required. |
| PhonePe and Razorpay live/sandbox qualification | `BLOCKED_HUMAN_ACTION` | Explicitly deferred by development payment policy; this is expected, not a failure. |

`PASS_LIVE` may be recorded only for a gate actually exercised against the
identified isolated staging deployment with retained, sanitized evidence.
Configuration review, local fixtures, or a successful setup step is not
`PASS_LIVE`.

Before loading credentials or allowing egress, run the offline-only preflight:

```powershell
python scripts/check-phase29e-staging-preflight.py
```

It inspects only named configuration entries and local storage paths, emits a
redacted JSON report, performs no network/database/provider call, and can report
at most `PASS_LOCAL`. Missing credentials are expected to report
`BLOCKED_CREDENTIALS`. Use
`docs/exec-plans/templates/phase29e-staging-evidence.json` for the later live
evidence record; its gates intentionally start blocked.

The preflight proves configuration structure only. It does not prove that a
target is isolated staging, that two identities are distinct, that configured
paths are approved deployment/backup/restore roots, or that any service works.
Those remain human/live gates. Reviewers must validate the evidence document
with `validate_staging_evidence` before accepting any `PASS_LIVE` entry; the
validator requires qualification identity, reviewer/operator, timestamp,
redacted command, exit status, artifact path, and artifact digest evidence and
keeps payments human-blocked.

Validate the evidence structure without printing its contents:

```powershell
python scripts/validate-phase29e-staging-evidence.py <evidence-json-path>
```

PhonePe and Razorpay must remain disabled. Do not request or load payment
credentials. Do not invoke checkout, status, callback, webhook, reconciliation,
capture, refund, or other provider paths. The development billing bypass is
permitted only in explicit local development tests and must be unset or false
for the staging deployment.

## Protected contracts

- Deterministic generation, canonical geometry, and hard validators remain
  authoritative.
- AI interpretation, topology, sizing, design intent, and Vastu explanation
  remain advisory and confirmation-required.
- Frozen Vastu rules and hashes must not change.
- Canonical dimensions remain integer millimetres.
- Architectural-brain maximum areas do not become hard feasibility caps.
- Wet-stack coordination remains soft.
- Project revisions remain immutable and ancestry-aware; exports remain tied to
  the exact persisted canonical revision.
- Candidate selection may normalize valid JSON at the API boundary but may not
  replace canonical candidate geometry with client or provider geometry.
- A qualification failure must not be repaired by weakening auth, RLS, grants,
  TLS, path containment, validators, environment guards, or protected contracts.

## Required environment variable names

The following are names only. Values belong in the approved staging secret and
configuration systems, never in this document, tracked files, shell history,
logs, screenshots, or evidence bundles.

### API runtime, database, auth, and network

```text
APP_ENV
AI_VASTU_AUTH_MODE
AI_VASTU_DATABASE_URL
AI_VASTU_DB_POOL_MIN_SIZE
AI_VASTU_DB_POOL_MAX_SIZE
AI_VASTU_DB_POOL_TIMEOUT_SECONDS
AI_VASTU_SUPABASE_URL
AI_VASTU_SUPABASE_JWT_AUDIENCE
AI_VASTU_WEB_ORIGINS
AI_VASTU_TRUSTED_HOSTS
AI_VASTU_REQUIREMENTS_PATH
AI_VASTU_GENERATION_UPLOAD_ROOT
FORWARDED_ALLOW_IPS
```

### Browser deployment

```text
NEXT_PUBLIC_AI_VASTU_API_BASE_URL
NEXT_PUBLIC_AI_VASTU_AUTH_MODE
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
```

Do not configure the development bearer-token variables in staging.

### Payment-disable boundary

```text
AI_VASTU_PAYMENT_GATEWAY
AI_VASTU_DEV_BILLING_BYPASS
```

No PhonePe or Razorpay variable is required or permitted for this
qualification.

### NVIDIA NIM-only routing and runtime budgets

```text
NVIDIA_API_KEY
AI_VASTU_REQUIREMENTS_PROVIDER
AI_VASTU_ARCHITECT_PROVIDER
AI_VASTU_VASTU_PROVIDER
AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER
AI_VASTU_REVISION_PROVIDER
AI_VASTU_PLAN_RECOGNITION_PROVIDER
AI_VASTU_NVIDIA_BASE_URL
AI_VASTU_NVIDIA_PRIMARY_MODEL
AI_VASTU_NVIDIA_VISION_MODEL
AI_VASTU_NVIDIA_ATTEMPT_TIMEOUT_SECONDS
AI_VASTU_NVIDIA_TOTAL_TIMEOUT_SECONDS
AI_VASTU_NVIDIA_RETRY_DELAY_SECONDS
AI_VASTU_NVIDIA_MAX_RETRY_AFTER_SECONDS
```

All six provider switches must be `nvidia_nim`. Do not configure or load
Ollama, APINEX, OpenRouter, or Gemini credentials into the qualification
process.

### Production-like application controls

```text
AI_VASTU_RATE_LIMIT_INTERPRET_PER_HOUR
AI_VASTU_RATE_LIMIT_GENERATION_PER_HOUR
AI_VASTU_RATE_LIMIT_PLAN_ANALYSIS_PER_HOUR
AI_VASTU_RATE_LIMIT_CHECKOUT_PER_HOUR
AI_VASTU_RATE_LIMIT_PAYMENT_STATUS_PER_HOUR
AI_VASTU_RATE_LIMIT_PAYMENT_WEBHOOK_PER_HOUR
AI_VASTU_HSTS_SECONDS
```

Payment limits remain configuration-only during this qualification; payment
routes must not be exercised.

### Operator-only qualification input

```text
AI_VASTU_TEST_POSTGRES_DSN
```

The repository defines no restore-target environment variable. The disposable
restore connection and destination paths must therefore be supplied directly to
the reviewed restore procedure through the approved operator secret mechanism.
They must not be added to tracked configuration.

## Exact human setup steps

1. Name the staging run with a unique qualification run ID and assign a human
   owner for target verification, mutation approval, evidence, cleanup, and
   rollback.
2. Identify the exact API origin, web origin, Supabase project, PostgreSQL
   server/database, requirements root, upload root, backup destination, and
   disposable restore target. Confirm none is production-linked.
3. Deploy the application against those staging resources using production-mode
   runtime guards. Local development remains in development mode; do not reuse
   local development configuration. Production-mode guards are required because
   the repository enables its full trusted-host, PostgreSQL rate-limit, HSTS,
   and production-settings checks only in that mode.
4. Keep the selected payment gateway disabled and the development billing
   bypass unset or false. Confirm that no payment credential is present.
5. Create separate database roles for migrations and application runtime. The
   runtime role must not own application tables, be superuser, hold `BYPASSRLS`,
   or use a Supabase service role for ordinary requests.
6. Require PostgreSQL TLS with certificate verification. Record sanitized
   server/database/role identity and TLS protocol/cipher evidence without the
   connection string.
7. Review and apply repository migrations in order using the migration role.
   Record every applied migration and the resulting schema version. Stop on an
   unexpected or destructive statement.
8. Revoke unnecessary public/default privileges. Grant the runtime role only
   the schema, table, sequence, and function privileges required by the API.
9. Inventory RLS enablement, force state, policies, owners, and security-definer
   functions/views for every applicable application-facing table. Ordinary
   qualification requests must use the deployed runtime path, not an owner,
   admin, or service-role bypass.
10. Create two dedicated non-admin Supabase identities: owner A and foreign user
    B. Complete any OTP, MFA, CAPTCHA, or email confirmation manually. Do not
    place access or refresh tokens in files or evidence.
11. Configure Supabase asymmetric JWT/JWKS verification, exact issuer and
    audience, bounded expiry, production-like Auth limits, the allowlisted web
    origin, and one deliberately unapproved origin for negative testing.
12. Configure exact proxy trust, trusted hosts, CORS origins, and conservative
    rate limits. The rate test window must be approved and must not affect other
    staging users.
13. Configure a staging-scoped, low-quota NVIDIA credential through the approved
    secret manager. Apply the explicit NVIDIA-only hosted profile. Do not load
    Ollama, APINEX, OpenRouter, or Gemini credentials into this process.
14. Mount isolated encrypted requirements and upload roots. Create an encrypted
    backup destination outside both roots. Resolve and record each absolute path
    before any write.
15. Create a new empty disposable PostgreSQL restore database plus empty
    requirements and upload restore roots. Keep restore disabled until the
    separate authorization checkpoint in the test sequence.
16. Prepare benign, non-sensitive JPG, PNG, and PDF plan fixtures and a cleanup
    inventory keyed by the qualification run ID.

## Safe live-test sequence

Run these steps serially. Record a status for each gate using only
`PASS_LOCAL`, `PASS_LIVE`, `BLOCKED_CREDENTIALS`, `BLOCKED_HUMAN_ACTION`,
`BLOCKED_EXTERNAL_SERVICE`, or `FAIL`.

1. **Target preflight, read-only.** Two humans verify the run ID and sanitized
   target identities. Confirm staging database, Supabase tenant, origins,
   storage roots, provider accounts, quotas, production-mode guards, disabled
   payments, disabled development bypass, and an empty disposable restore
   target. Stop if any identity is ambiguous.
2. **Configuration preflight, no provider request.** Start the deployment and
   run `python scripts/check-phase29e-staging-preflight.py`, then inspect only
   redacted readiness/configuration output. Verify exact host/CORS, NVIDIA-only
   provider routing, timeouts, storage roots, and database identity.
   Do not run `pnpm phase25:launch`: that production launch gate intentionally
   rejects disabled payments and is outside this non-payment qualification.
3. **PostgreSQL/TLS inspection, read-only.** Verify TLS certificate validation,
   database/server/runtime-role identity, migration inventory, object ownership,
   effective grants, default/public grants, RLS enablement/force state, policy
   definitions, and absence of superuser/owner/`BYPASSRLS` runtime authority.
4. **Authorized disposable DB smoke.** After the staging mutation window is
   approved, run the repository persistence smoke against
   `AI_VASTU_TEST_POSTGRES_DSN`. Record created identifiers, two-revision
   ancestry, payload hash, reload result, and cleanup inventory. This direct
   repository smoke does not by itself qualify JWT or RLS.
5. **JWT/JWKS matrix.** Through the deployed API, verify owner A succeeds and
   missing, malformed, expired, wrong-issuer, wrong-audience, unknown-key, and
   foreign-user tokens fail safely. Verify JWKS key selection/refresh failure
   does not accept a token. Never retain tokens or authorization headers.
6. **Ownership/RLS matrix.** Owner A creates the tagged project. Foreign user B
   must be unable to list, read, infer, mutate, generate against, select, revise,
   export, or delete owner A resources, including guessed direct IDs, nested
   routes, and upload paths. Repeat relevant checks after persistence/reload.
7. **CORS, host, and bounded rate limits.** Verify allowed-origin preflight and
   request behavior, disallowed-origin behavior, rejected untrusted hosts, real
   client-IP derivation through the reviewed proxy chain, a bounded 429, and
   recovery after the window. Do not load-test or approach provider spend limits.
8. **Provider probes.** Only after provider credentials and request budgets are
   approved, run `pnpm phase29c:live` once. Retain only sanitized provider/model,
   correlation, timing, and status evidence. The command's PNG probe does not
   complete JPG/PDF qualification.
9. **JPG/PNG/PDF recognition.** Upload the three prepared fixtures through the
   owner API workflow and invoke persisted plan analysis for each. Verify NVIDIA
   vision routing, MIME/content validation, bounded timeouts/errors, sanitized
   failures, uncertainty, and mandatory human confirmation. Reject provider
   output that attempts to become canonical geometry.
10. **NVIDIA interpretation.** Submit the synthetic requirements brief and
    verify the configured hosted text/reasoning route, schema validation, safe timeout/
    error behavior, and human confirmation. Do not retain prompt or raw response
    bodies in the evidence bundle.
11. **Non-payment workflow E2E.** As owner A, execute auth -> project creation ->
    requirements -> optional plan upload -> AI interpretation -> confirmation ->
    deterministic candidate generation -> hard validation -> frozen Vastu
    scoring -> candidate selection -> PostgreSQL persistence -> reload -> new
    immutable revision -> export. Record canonical hashes and ancestry. Do not
    invoke an entitlement or payment route; if the disabled-gateway policy
    prevents an otherwise authorized generation, record that boundary honestly
    rather than enabling a provider or development bypass.
12. **AI failure checks.** Within the approved low request budget, exercise a
    controlled timeout/error or use provider-supported safe fault injection.
    Confirm failures are sanitized and never fabricate geometry, skip human
    confirmation, or bypass deterministic validation. Do not intentionally
    exhaust or invalidate shared credentials.
13. **Backup creation.** Run `scripts/backup-production.ps1` against the approved
    staging database and roots with an existing absolute output directory outside
    both storage roots. Verify the PostgreSQL custom dump, requirements archive,
    upload archive, SHA-256 hashes, source revision, migration version, and
    encrypted retention location. A backup success is not a restore pass.
14. **Restore authorization checkpoint.** Stop and obtain explicit human
    authorization immediately before restore. Reconfirm the new empty disposable
    database and resolved restore roots. Without that authorization, record the
    restore gate as `BLOCKED_HUMAN_ACTION` and skip it.
15. **Disposable restore drill.** Restore only into the disposable target. Before
    extraction, reject absolute/drive-qualified members, `..` traversal,
    symlinks/junctions, unexpected members, and any resolved destination outside
    the approved root. Verify schema/migrations, representative record counts,
    ownership relationships, revision ancestry/hashes, requirements manifests,
    and upload hashes. Never restore over active staging.
16. **Cleanup and evidence review.** Perform the cleanup below, prove that only
    run-tagged resources were removed, and have QA/security/release reviewers
    reconcile every claim with retained evidence before assigning `PASS_LIVE`.

## Cleanup procedure

1. Freeze the run inventory and verify every candidate target by exact ID and
   resolved absolute path. Never use a broad glob, inferred root, or recursive
   deletion against an unresolved path.
2. Delete only qualification-tagged exports, revisions/projects where supported,
   requirements records, and uploads belonging to owner A and the run ID.
3. Remove the persistence-smoke records by their recorded exact IDs. Confirm
   foreign and pre-existing staging records are unchanged.
4. Delete the two disposable Auth identities only after confirming they are the
   run identities and are not reused elsewhere.
5. Revoke or rotate temporary staging provider/database credentials according to
   the operator policy. Never record their values.
6. Destroy only the positively identified disposable restore database and its
   restore roots after evidence capture and explicit target verification.
7. Retain sanitized evidence and backup retention metadata; remove raw uploaded
   fixtures or provider payloads that are not required by policy.
8. Confirm no qualification record, upload, active token, temporary grant, or
   restore resource remains. Record any human-owned residual action.

## Rollback procedure

1. Stop the qualification runner and staging-only traffic created for the run.
2. Disable the affected staging route or deployment if isolation, auth, or secret
   handling is in doubt.
3. Revoke suspect temporary credentials and restore the previously recorded
   staging secret/configuration version.
4. Roll the application back to the recorded prior staging artifact. Preserve
   sanitized logs and request IDs for diagnosis.
5. Prefer reviewed forward database remediation. Run a down migration only when
   it is explicitly supported, separately reviewed, and authorized.
6. Do not rewrite immutable revisions. Do not restore a backup over active
   staging. Any broader data restore requires a new explicit human decision.
7. Remove only verified run-tagged records and the exact disposable restore
   target. If cleanup identity is uncertain, stop and leave the item for the
   named human owner.
8. Keep affected gates blocked or failed; rollback never converts a result to
   `PASS_LIVE`.

## Expected evidence artifacts

Store only sanitized evidence in the approved evidence location:

- qualification run ID, UTC timestamps, reviewers, and deployment/source commit;
- redacted environment-variable presence checklist by name;
- sanitized API/web/Supabase/database/storage/provider target identities;
- TLS verification, migration inventory, database ownership, effective grants,
  RLS policy inventory, and runtime-role capability checks;
- owner/foreign-user HTTP status and response-hash matrix;
- JWT/JWKS negative matrix without tokens or headers;
- allowed/disallowed CORS, trusted-host, proxy-client-IP, bounded rate-limit, and
  recovery traces;
- provider/model routing, safe correlation IDs, timings, JPG/PNG/PDF fixture
  hashes, and timeout/error categories without prompts, payloads, or secrets;
- E2E project/revision/candidate/export IDs, canonical document hashes,
  deterministic hard-validation result, frozen Vastu result, and ancestry;
- backup artifact names, sizes, SHA-256 hashes, migration/source revision,
  encrypted retention identifier, and path-containment checks;
- explicit restore authorization record, disposable target identity, restore
  integrity comparison, and destruction confirmation when performed;
- exact cleanup inventory and residual-action report;
- final per-gate table using only the permitted Phase 29E status labels.

Do not retain bearer/refresh tokens, database URLs, API keys, authorization
headers, raw provider responses, raw sensitive prompts/uploads, `.env.production`,
or secret-manager screenshots.

## Stop conditions

Stop immediately, preserve sanitized evidence, and do not claim `PASS_LIVE` if:

- the target is production, production-linked, or cannot be positively
  distinguished from production;
- PhonePe or Razorpay is enabled, a payment credential is present, a payment
  route is invoked, or any payment-provider network activity occurs;
- the development billing bypass is active outside explicit local development;
- TLS certificate verification is disabled or fails;
- the runtime database identity owns application objects, is privileged,
  bypasses RLS, or has excessive grants;
- migrations are unexpected, destructive, incomplete, or drifted;
- owner/foreign-user isolation fails or resource existence leaks;
- JWT signature, issuer, audience, expiry, role, or key selection fails open;
- CORS, trusted-host, proxy identity, or rate-limit behavior is unsafe;
- any secret, token, credential, connection string, or sensitive payload appears
  in a tracked file, log, screenshot, command history, or evidence artifact;
- provider routing/model policy differs from the explicit NVIDIA hosted profile,
  retries/cost exceed the approved ceiling, or an external service is unstable;
- AI output becomes authoritative geometry, bypasses confirmation/validation, or
  changes deterministic, Vastu, unit, ranking, or revision contracts;
- backup hashes fail, an archive member escapes containment, a symlink/junction
  is encountered, or the backup destination overlaps a source root;
- restore lacks immediate explicit human authorization, the target is not new
  and disposable, or a command could overwrite active staging;
- qualification records cannot be enumerated exactly for cleanup.

Use `FAIL` for an exercised product/configuration defect,
`BLOCKED_CREDENTIALS` for absent required credentials,
`BLOCKED_HUMAN_ACTION` for missing setup or authorization, and
`BLOCKED_EXTERNAL_SERVICE` only for verified third-party unavailability. Never
convert missing or local-only evidence into `PASS_LIVE`.
