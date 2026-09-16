# Phase 18 — PostgreSQL/Supabase production persistence

Phase 18 removes `PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED` without changing canonical geometry,
solver behavior, Vastu doctrine, or project revision semantics.

## Adds

- Psycopg 3 production PostgreSQL adapter with connection pooling.
- Supabase-compatible prepared-statement configuration.
- PostgreSQL migration for projects + immutable revisions.
- Transactional `FOR UPDATE` project-head concurrency control.
- Environment-driven repository factory.
- Fail-closed production/staging startup without `AI_VASTU_DATABASE_URL`.
- FastAPI repository lifetime ownership.
- Deterministic persistence gate and policy tests.

## Release-gate delta

Phase 17 blockers: 5.

Phase 18 blockers: 4.

Removed only:

- `PRODUCTION_PERSISTENCE_NOT_IMPLEMENTED`

Remaining:

- `VASTU_SPEC_NOT_FROZEN`
- `VASTU_RULESET_EMPTY`
- `VASTU_RULE_BUNDLE_NOT_PINNED`
- `AUTHORIZATION_NOT_IMPLEMENTED`
## Live PostgreSQL qualification

`persistence:live` is intentionally separate from ordinary CI. Run it against a disposable or
dedicated PostgreSQL database after applying the Phase 18 migration. The included PostgreSQL 17
Compose file provides a deterministic local qualification target.

