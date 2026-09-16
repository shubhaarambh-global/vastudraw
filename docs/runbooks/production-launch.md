# Production launch runbook

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

### Razorpay

- create production/live API credentials;
- configure the webhook endpoint over HTTPS;
- use a dedicated webhook secret;
- verify `X-Razorpay-Signature` against the raw request body;
- keep webhook processing idempotent;
- test subscription lifecycle and webhook retries before enabling live checkout.

### OpenAI

- keep API credentials server-side only;
- use the configured model through `AI_VASTU_OPENAI_MODEL`;
- retain Phase 24 structured schema validation and `store:false`;
- enforce application + edge rate limits and monitor cost/usage.

## Infrastructure

1. Apply all PostgreSQL/Supabase migrations, including Phase 25.
2. Mount durable encrypted storage for requirements/intake artifacts.
3. Load production secrets from the hosting secret manager.
4. Set exact CORS origins and trusted hosts; never use `*`.
5. Put the API behind HTTPS and an edge/WAF or equivalent abuse-control layer.
6. Run `pnpm validate`.
7. Run `pnpm phase25:launch` with the real production environment.
8. Run staging payment/webhook and full generation smoke tests.
9. Create and verify a pre-launch backup.
10. Deploy, then verify `/health` and `/system/release-readiness`.

## Post-launch checks

- generation success/error/latency;
- PostgreSQL connection saturation;
- 429 and 503 rate;
- OpenAI spend and request volume;
- Razorpay webhook failures/retries;
- failed auth volume;
- storage capacity;
- backup completion;
- restore drill schedule.

Do not log prompts, bearer tokens, API keys, payment secrets, or raw uploaded files
in application logs.
