# ADR-047 — Production hardening and commercial launch gate

## Status

Accepted.

## Decision

Phase 25 adds defense-in-depth around the Phase 24 commercial generation path.

The deterministic planning engine, frozen Vastu rules, scoring, project revision
semantics, and Phase 23 billing semantics remain unchanged.

Production must fail closed when:
- development authentication is enabled;
- PostgreSQL persistence is unavailable;
- Supabase Auth is not HTTPS-configured;
- CORS origins or trusted hosts are wildcards;
- Razorpay production credentials/webhook secret are absent;
- live requirements interpretation is configured without OpenAI credentials;
- server-side rate limits are disabled;
- the frozen production Vastu bundle hash differs from the approved Phase 20B hash.

The API adds security headers, request IDs, structured request logs and a
PostgreSQL-backed rate limiter on expensive commercial endpoints.

Edge/provider rate limiting remains mandatory. Application rate limiting is not
treated as a replacement for WAF/CDN/Supabase protections.

Backups must cover both PostgreSQL and the configured persistent file roots.
