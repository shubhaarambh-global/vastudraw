# ADR-034 — Project persistence boundary

## Decision

Domain code depends on `ProjectRepository`, not on a database vendor. Phase 11 includes a transactional SQLite reference adapter using only the Python standard library. It proves schema, transaction, reload, hash-integrity and optimistic-concurrency semantics locally.

The production deployment target remains PostgreSQL/Supabase. A PostgreSQL adapter must implement the same repository contract and pass the same persistence conformance suite before production use.

SQLite is not declared the production database by this ADR.
