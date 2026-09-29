# Phase 29E - Live / Deployment End-to-End Qualification

Status: **SAFE LOCAL PREPARATION COMPLETE; LIVE EXECUTION BLOCKED**

## Qualification boundary

- Phase 29D has a reviewed `PASS_LOCAL` tree, but the required checkpoint commit
  is `BLOCKED_HUMAN_ACTION` because the managed session cannot write `.git` and
  therefore cannot create `index.lock`.
- No production-qualified tag is permitted.
- The current process contains no production database, Supabase, OpenRouter,
  Gemini, PhonePe, deployment, or hybrid-provider configuration.
- The repository-local, Git-ignored `.env.production` is a legacy pre-Phase-29 profile. It
  uses superseded database/origin/provider keys, selects `openai`, and lacks the
  current storage, payment, PhonePe, OpenRouter, Gemini, and hybrid-provider
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
| PostgreSQL grants, ownership, migrations, and applicable RLS | `BLOCKED_CREDENTIALS` | Local migrations/policy tests exist; deployed metadata has not been inspected. |
| Live ownership denial and revision persistence | `BLOCKED_CREDENTIALS` | Requires an approved isolated staging database and two test identities. |
| Backup creation | `BLOCKED_CREDENTIALS` | No approved database/storage target or backup destination is configured. |
| Disposable restore drill | `BLOCKED_HUMAN_ACTION` | Requires an explicitly authorized new disposable restore database and retention/cleanup decision. |
| Supabase/JWT issuer, audience, expiry, rotation, and ownership denial | `BLOCKED_CREDENTIALS` | No current Supabase configuration or test-user tokens are loaded. |
| Deployed CORS and rate limits | `BLOCKED_HUMAN_ACTION` | No reviewed deployment URL, edge/proxy identity, or authorized rate-test window is supplied. |
| OpenRouter production-equivalent live check | `BLOCKED_CREDENTIALS` | `OPENROUTER_API_KEY` and current provider switches are absent. |
| Direct Gemini JPG/PNG/PDF live check | `BLOCKED_CREDENTIALS` | `GEMINI_API_KEY` and current provider switches are absent. |
| AI deterministic-authority boundary | `PASS_LOCAL` | Existing qualified local gates keep AI advisory and deterministic geometry/validators authoritative. |
| PhonePe sandbox checkout and provider-status reconciliation | `BLOCKED_CREDENTIALS` | No sandbox merchant/client/webhook configuration is loaded. |
| PhonePe callback reachability and provider-console setup | `BLOCKED_HUMAN_ACTION` | Requires a reviewed HTTPS deployment callback and sandbox account configuration. |
| Payment replay/duplicate/exactly-once behavior | `PASS_LOCAL` | Phase 29D local fixture, adversarial, repository, and API evidence passed; genuine sandbox delivery remains blocked. |
| Production-equivalent end-to-end workflow | `BLOCKED_CREDENTIALS` | No database, auth, AI, or payment credentials are loaded; a reviewed isolated deployment, dedicated test users, and human confirmation are additional prerequisites. |

## Sequential live procedure

1. Restore `.git` write access, selectively stage the reviewed Phase 29D
   allowlist, inspect cached name/status, stat, check, and complete diff, create
   a normal checkpoint commit, and record its hash. Do not tag.
2. Identify the exact isolated staging deployment, database, Supabase project,
   AI provider accounts, PhonePe sandbox merchant, callback URLs, and rollback
   owner. Print only sanitized identity and credential-presence evidence.
3. Inspect PostgreSQL connectivity, verified TLS, server/database/application
   role identity, grants, ownership, migration head, RLS enablement/force state,
   and policies read-only. Do not apply migrations to production.
4. On explicitly approved isolated staging only, use two test identities to
   exercise ownership denial, revision persistence/ancestry, reload, and cleanup.
5. Verify Supabase/JWT signature algorithm, exact issuer and audience, expiry/
   not-before, JWKS rotation behavior, malformed-token denial, cross-owner
   denial, deployed CORS, and conservative deployed rate limits.
6. Exercise OpenRouter with a minimal non-sensitive reasoning fixture and direct
   Gemini with non-sensitive JPG, PNG, and PDF fixtures. Verify bounded input,
   MIME/content validation, timeouts, sanitized failures, human confirmation,
   and continued deterministic geometry authority.
7. Use PhonePe sandbox only. Exercise checkout, pending, success, failure,
   signed callback, duplicate/replay/reordered/concurrent delivery,
   reconciliation, uniqueness boundaries, and exactly-once entitlement. Never
   spend real money without explicit human approval.
8. Create a backup from approved staging, then restore only into a newly created
   disposable database. Verify schema, ownership isolation, revision ancestry,
   representative hashes, file manifests, and cleanup/retention evidence.
9. Exercise the production-equivalent flow with dedicated test identities:
   auth -> project -> requirements -> optional JPG/PNG/PDF upload -> AI
   interpretation -> human confirmation -> candidate generation -> deterministic
   validation -> Vastu evaluation -> selection -> persistence -> reload ->
   revision -> export -> sandbox entitlement/payment.
10. Run independent DB/Auth, AI, payment, backup/restore, E2E, adversarial,
    security, QA, and release reviews. A production tag remains forbidden while
    any required live gate is blocked or failed.

## Required human actions

1. Run Codex in a workspace where `.git` is writable, or perform the exact
   reviewed selective Phase 29D stage/commit and provide the resulting hash.
2. Identify and authorize an isolated staging deployment and disposable restore
   target. Provide deployment/database/Supabase/OpenRouter/Gemini/PhonePe
   sandbox credentials through the approved secret mechanism, never chat or a
   tracked file.
3. Provide or authorize two dedicated Supabase test users and any required
   OTP/MFA/CAPTCHA completion.
4. Configure/approve an externally reachable HTTPS PhonePe sandbox callback and
   provider-console allowlisting.
5. Authorize the staging mutation, conservative rate-limit test window, backup,
   and disposable restore drill. No production write or real-money transaction
   is implied.

## Stop conditions

Stop and classify `FAIL` for disabled TLS verification, excessive database
grants, cross-tenant access, migration drift that cannot be explained, dev
billing bypass in production, secret leakage, AI authority inversion, unsigned
payment acceptance, entitlement before authoritative success, or duplicate
entitlement. Classify a genuine provider outage with otherwise reviewed valid
configuration as `BLOCKED_EXTERNAL_SERVICE`.
