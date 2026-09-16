# Phase 19 — Authentication, Authorization, and Dashboard

Phase 19 removes `AUTHORIZATION_NOT_IMPLEMENTED` without changing canonical geometry,
solver behavior, Vastu doctrine, or immutable revision hashes.

## Security boundary

- Supabase Auth is the production identity provider.
- The API verifies user access tokens against the Supabase asymmetric JWKS endpoint.
- Only ES256/RS256 access tokens with issuer, audience, expiry, subject, and authenticated
  role checks are accepted by the production verifier.
- A deterministic bearer-token verifier exists for local development/tests only and is
  rejected when `APP_ENV` is `production` or `staging`.
- Project ownership is stored separately from PlanDocument geometry and revision payloads.
- Project/revision endpoints return 404 for another user's project to avoid existence leaks.
- Generation requires an authenticated user.
- CORS explicitly allows `Authorization` and `Content-Type` only.

## Persistence

Phase 19 adds `public.ai_vastu_project_owners` with one owner per project. New project
creation writes the project and owner row in one database transaction. The ownership table
has RLS enabled and grants are revoked from Supabase `anon`/`authenticated` Data API roles;
the FastAPI service remains the authoritative access boundary for project workflows.

## Dashboard

The Next.js root route is now a real project dashboard. It supports:

- Supabase email/password sign-in and sign-up;
- authenticated project listing;
- authenticated project creation;
- project cards with revision state;
- direct navigation to the deterministic editor at `/editor`;
- a configuration-safe shell when Supabase browser variables are not present.

The dashboard never authorizes itself. It only supplies a bearer token; the API performs
all project ownership checks.

## Release-gate delta

Phase 18 blockers: 4.

Phase 19 blockers: 3.

Removed only:

- `AUTHORIZATION_NOT_IMPLEMENTED`

Remaining:

- `VASTU_SPEC_NOT_FROZEN`
- `VASTU_RULESET_EMPTY`
- `VASTU_RULE_BUNDLE_NOT_PINNED`

## Supabase configuration

Web:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `NEXT_PUBLIC_AI_VASTU_API_BASE_URL`

API:

- `AI_VASTU_AUTH_MODE=supabase`
- `AI_VASTU_SUPABASE_URL`
- `APP_ENV=production` or `staging` in deployed environments

The Supabase project should use asymmetric JWT signing keys for production verification.

## Immediate local dashboard preview

For `next dev`, the dashboard can use the explicit development identity without Supabase:

- `NEXT_PUBLIC_AI_VASTU_AUTH_MODE=development`
- `NEXT_PUBLIC_AI_VASTU_DEV_BEARER_TOKEN=dev-local-token`
- API `AI_VASTU_DEV_BEARER_TOKEN=dev-local-token`

This browser development mode is disabled when Next.js runs with `NODE_ENV=production`, and
the API independently rejects development authentication whenever `APP_ENV` is
`production` or `staging`.
