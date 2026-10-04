# Production launch runbook

Phase 29A establishes a coherent fail-closed configuration contract. Phase 29D
adds server-side PhonePe Standard Checkout for one-time project purchases and
atomic entitlement settlement. Neither phase, by itself, qualifies live
production services or payments. Razorpay remains optional and is not required
for a PhonePe profile.

## Canonical production configuration

- `APP_ENV=production` and `AI_VASTU_AUTH_MODE=supabase`;
- `AI_VASTU_DATABASE_URL` is the single PostgreSQL URL used by repositories,
  billing and rate limiting;
- `AI_VASTU_WEB_ORIGINS` and `AI_VASTU_TRUSTED_HOSTS` contain explicit values;
- `AI_VASTU_REQUIREMENTS_PATH` and `AI_VASTU_GENERATION_UPLOAD_ROOT` are
  absolute durable paths;
- `AI_VASTU_DEV_BILLING_BYPASS` is unset or false;
- `AI_VASTU_PAYMENT_GATEWAY` is explicit;
- NVIDIA NIM handles text/reasoning and plan recognition through the fixed
  hosted API Catalog base URL `https://integrate.api.nvidia.com/v1`.
- NVIDIA NIM has explicit per-attempt and total deadlines. Its single same-model
  transient retry count is fixed in application code and is not operator-configurable.
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

- configure production credentials and callbacks only through the secret
  manager and the official PhonePe account workflow;
- configure the HTTPS redirect and callback endpoints from the reviewed public
  API origin;
- apply the Phase 29D payment-order migration before enabling checkout;
- schedule `python scripts/reconcile-phonepe-payments.py` as a bounded recovery
  job for pending or ambiguous orders;
- drain or explicitly reconcile all in-flight orders before changing the
  selected production gateway; owner status routes follow the active gateway;
- confirm callbacks by querying authoritative PhonePe order status; callback
  fields never grant entitlement directly;
- keep monthly/yearly checkout disabled until a recurring AutoPay mandate flow
  and its lifecycle semantics are separately implemented and qualified;
- treat local configuration and fixture acceptance as offline evidence only.

### Optional Razorpay

- create production/live API credentials;
- configure the webhook endpoint over HTTPS;
- use a dedicated webhook secret;
- verify `X-Razorpay-Signature` against the raw request body;
- keep webhook processing idempotent;
- test subscription lifecycle and webhook retries before enabling live checkout.

### NVIDIA NIM

- keep `NVIDIA_API_KEY` server-side only and never expose it to the web app;
- use `nvidia/nemotron-3-ultra-550b-a55b` as the sole active primary for
  requirements and architectural reasoning;
- keep `nvidia/nemotron-3.5-lightning-30b-a3b` inactive and marked
  `NOT_QUALIFIED_TIMEOUT`; do not configure it as a fallback;
- use `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` for plan recognition;
- render PDF pages locally to bounded images before recognition; never send raw
  PDF bytes to NVIDIA or introduce another cloud document provider;
- `/requirements/interpret` remains API-compatible with reference uploads, but
  its NVIDIA text adapter uses filenames as context only and does not claim to
  inspect file contents. Use persisted Analyze Plan for visual plan recognition;
- keep OpenRouter and direct Gemini adapters legacy/inactive. Their credentials
  are not part of the NVIDIA profile and production settings reject routing to
  them;
- retain structured schema validation and non-authoritative AI boundaries;
- enforce application + edge rate limits and monitor cost/usage.

Configure the bounded runtime values explicitly (seconds):

```text
AI_VASTU_NVIDIA_ATTEMPT_TIMEOUT_SECONDS=120
AI_VASTU_NVIDIA_TOTAL_TIMEOUT_SECONDS=240
AI_VASTU_NVIDIA_RETRY_DELAY_SECONDS=0
AI_VASTU_NVIDIA_MAX_RETRY_AFTER_SECONDS=0
```

Do not add environment variables for attempt counts. NVIDIA NIM may retry the
same pinned model once only after `unavailable` or `timeout`, within the same
total deadline. It never substitutes a text or vision model and never crosses
providers.

## Phase 29C provider evidence

Offline factory and synthetic-response check (no credentials or network calls):

```powershell
pnpm phase29c:check
```

Live provider check, only after loading a reviewed NVIDIA credential and the
exact NVIDIA-only provider switches:

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

1. Apply all PostgreSQL/Supabase migrations, including Phase 25 and Phase 29D.
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
7. Run `pnpm phase29c:live` only against an explicitly reviewed NVIDIA account.
   A hosted API Catalog pass qualifies development/staging only; keep
   `NVIDIA_NIM_PRODUCTION_ENTITLEMENT = BLOCKED_HUMAN_ACTION` until an
   appropriate NVIDIA AI Enterprise or production endpoint arrangement exists.
8. Run `pnpm phase25:launch` only against an explicitly reviewed target. The
   command connects to PostgreSQL and writes/removes storage probes.
9. Run staging payment/webhook and full generation smoke tests.
   For PhonePe, exercise checkout creation, redirect/return, repeated callbacks,
   reconciliation after timeout, amount mismatch rejection, and replay safety.
10. Create and verify a pre-launch backup.
11. Deploy, then verify `/health` and `/system/release-readiness`.

## Post-launch checks

- generation success/error/latency;
- PostgreSQL connection saturation;
- 429 and 503 rate;
- NVIDIA NIM spend and request volume;
- selected payment-gateway webhook failures/retries;
- failed auth volume;
- storage capacity;
- backup completion;
- restore drill schedule.

Do not log prompts, bearer tokens, API keys, payment secrets, or raw uploaded files
in application logs.
