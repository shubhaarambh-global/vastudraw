# Phase 18 — Production persistence

Phase 18 introduces a PostgreSQL/Supabase production adapter behind the existing
`ProjectRepository` contract. SQLite remains a local/reference adapter only.

## Runtime contract

- `APP_ENV=production` or `APP_ENV=staging` requires `AI_VASTU_DATABASE_URL`.
- Missing PostgreSQL configuration in those environments fails closed at startup.
- Development/test may continue to use SQLite through `AI_VASTU_SQLITE_PATH`.
- PostgreSQL schema is migration-owned; the application never auto-creates production tables.
- Repository startup verifies both Phase 18 tables exist before serving requests.

## Concurrency and immutability

Appending a revision obtains a row lock on the owning project using `FOR UPDATE`, validates
`expected_parent_revision_id`, inserts the immutable revision, and advances the project head
inside one database transaction. Revision numbers are unique per project and revisions cannot
cascade-delete with a project.

## Supabase connectivity

The adapter accepts a normal PostgreSQL connection URL. It disables Psycopg automatic prepared
statements so that Supabase transaction-pooler URLs are compatible. Production operators should
choose direct, session-pooler, or transaction-pooler connectivity appropriate to their deployment.
