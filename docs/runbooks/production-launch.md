# Production launch runbook

Phase 29A establishes a coherent fail-closed configuration contract. It does
not qualify production services or payments. PhonePe is the launch direction,
but its checkout/webhook implementation remains a Phase 29D blocker. Razorpay
is retained as an optional gateway and is not required for a PhonePe profile.

## Canonical production configuration

- `APP_ENV=production` and `AI_VASTU_AUTH_MODE=supabase`;
- `AI_VASTU_DATABASE_URL` is the single PostgreSQL URL used by repositories,
  billing and rate limiting;
- `AI_VASTU_WEB_ORIGINS` and `AI_VASTU_TRUSTED_HOSTS` contain explicit values;
- `AI_VASTU_REQUIREMENTS_PATH` and `AI_VASTU_GENERATION_UPLOAD_ROOT` are
  absolute durable paths;
- `AI_VASTU_DEV_BILLING_BYPASS` is unset or false;
- `AI_VASTU_PAYMENT_GATEWAY` is explicit;
- OpenRouter handles text/reasoning and direct Gemini handles plan recognition,
  using the qualified pinned models.
- OpenRouter and Gemini have explicit per-attempt and total deadlines. Retry
  counts are fixed in application code and are not operator-configurable.
- `AI_VASTU_RATE_LIMIT_PLAN_ANALYSIS_PER_HOUR` limits only `POST` requests to
  persisted plan analysis. Analysis reads and plan confirmation remain outside
  that scope.

## Provider controls to configure

### Supabase

Before public launch:
- enable RLS on application-facing tables and review Security Advisor;
- enforce SSL and configure network restrictions where appropriate;
- protect organization/admin accounts with MFA;
- configure production Auth rate limits and CAPTCHA/bot protection;
- use a production SMTP provider for authentication email;
- configure backups and the required recovery objective (PITR if required);
- test migrations in staging before applying them to production.

### PhonePe

- do not enable checkout until the Phase 29D adapter, verification and
  idempotency fixtures are qualified;
- configure production credentials and callbacks only through the secret
  manager and the official PhonePe account workflow;
- treat Phase 29A configuration acceptance as configuration evidence only.

### Optional Razorpay

- create production/live API credentials;
- configure the webhook endpoint over HTTPS;
- use a dedicated webhook secret;
- verify `X-Razorpay-Signature` against the raw request body;
- keep webhook processing idempotent;
- test subscription lifecycle and webhook retries before enabling live checkout.

### OpenRouter and direct Gemini

- keep both API credentials server-side only;
- use OpenRouter for requirements, architectural reasoning, Vastu reasoning,
  Architectural Brain and revisions;
- use direct Gemini for the persisted Analyze Plan recognition route;
- retain the existing `/requirements/interpret` compatibility behavior: visual
  requirements attachments use the pinned OpenRouter vision model. This is
  separate from persisted Analyze Plan, but whether it should remain on
  OpenRouter is an unresolved launch decision;
- retain structured schema validation and non-authoritative AI boundaries;
- enforce application + edge rate limits and monitor cost/usage.

Configure the bounded runtime values explicitly (seconds):

```text
AI_VASTU_OPENROUTER_ATTEMPT_TIMEOUT_SECONDS=120
AI_VASTU_OPENROUTER_TOTAL_TIMEOUT_SECONDS=240
AI_VASTU_OPENROUTER_RETRY_DELAY_SECONDS=0
AI_VASTU_OPENROUTER_MAX_RETRY_AFTER_SECONDS=0
AI_VASTU_GEMINI_ATTEMPT_TIMEOUT_SECONDS=90
AI_VASTU_GEMINI_TOTAL_TIMEOUT_SECONDS=181
AI_VASTU_GEMINI_RETRY_DELAY_SECONDS=1
AI_VASTU_GEMINI_MAX_RETRY_AFTER_SECONDS=5
```

Do not add environment variables for attempt counts. OpenRouter may try its
pinned primary once and its approved fallback once. Gemini may make one bounded
retry for a transient failure and never switches provider or model.

## Phase 29C provider evidence

Offline factory and synthetic-response check (no credentials or network calls):

```powershell
pnpm phase29c:check
```

Live provider check, only after loading reviewed credentials and the exact
hybrid provider switches:

```powershell
pnpm phase29c:live
```

The live checker constructs providers through the application runtime factories
and sends synthetic text and image inputs. It reports each provider as
`PASS_LIVE`, `FAIL`, or `BLOCKED_CREDENTIALS`. It does not print prompts, image
bytes, credentials, authorization headers, or raw provider response bodies.
`BLOCKED_CREDENTIALS` and `FAIL` are non-zero exits. Do not run this command
against a provider account or target that has not been explicitly reviewed.

## Infrastructure

1. Apply all PostgreSQL/Supabase migrations, including Phase 25.
2. Mount durable encrypted storage for requirements/intake artifacts.
3. Load production secrets from the hosting secret manager.
4. Set exact CORS origins and trusted hosts; never use `*`.
5. Put the API behind HTTPS and an edge/WAF or equivalent abuse-control layer.
   Set Uvicorn `FORWARDED_ALLOW_IPS` to the exact ingress/sidecar proxy IPs or
   CIDRs, never `*`, then verify in staging that `request.client.host` resolves
   to the real client address. The application rate limiter is IP-keyed; an
   incorrect proxy trust chain can collapse users into one shared bucket.
   Schedule retention cleanup for expired `ai_vastu_rate_limit_windows` rows.
6. Run `pnpm validate`.
7. Run `pnpm phase29c:live` only against explicitly reviewed provider accounts.
8. Run `pnpm phase25:launch` only against an explicitly reviewed target. The
   command connects to PostgreSQL and writes/removes storage probes.
9. Run staging payment/webhook and full generation smoke tests.
10. Create and verify a pre-launch backup.
11. Deploy, then verify `/health` and `/system/release-readiness`.

## Post-launch checks

- generation success/error/latency;
- PostgreSQL connection saturation;
- 429 and 503 rate;
- OpenRouter/Gemini spend and request volume;
- selected payment-gateway webhook failures/retries;
- failed auth volume;
- storage capacity;
- backup completion;
- restore drill schedule.

Do not log prompts, bearer tokens, API keys, payment secrets, or raw uploaded files
in application logs.
