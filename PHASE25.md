# Phase 25 — Production Hardening + Commercial Launch

Phase 25 is the final roadmap phase.

It hardens the already-frozen Phase 24 product without changing the authoritative
generation, Vastu, scoring, billing, or project-revision algorithms.

## Added production controls

- fail-closed production environment validation;
- API security headers and request IDs;
- structured request logging;
- PostgreSQL-backed fixed-window rate limiting for expensive endpoints;
- explicit launch gate for Supabase/Auth/PostgreSQL/Razorpay/OpenAI configuration;
- frozen Vastu bundle verification;
- backup and restore runbook;
- CI validation workflow;
- production container examples;
- third-party/license audit helper;
- security and launch runbooks.

## Expensive paths protected in production

- `/requirements/interpret`
- `/confirmed-generation/projects/*`
- `/billing/checkout`

Rate limiting is keyed by a SHA-256 digest of the bearer token when present,
otherwise by client address. Raw bearer tokens are never stored by the limiter.

Application rate limiting is defense-in-depth. Production launch still requires
provider/edge abuse protection and Supabase Auth rate-limit/CAPTCHA configuration.

## Persistent files

The existing Phase 22/24 stores already fail closed in production unless explicit
persistent paths are configured. Phase 25 does not replace those authoritative
stores. Deploy them on durable encrypted storage and include them in backups.

## Launch principle

`pnpm validate` proves repository correctness without requiring live secrets.

`pnpm phase25:launch` is the production-environment gate and MUST be run with the
real production environment loaded immediately before launch.
