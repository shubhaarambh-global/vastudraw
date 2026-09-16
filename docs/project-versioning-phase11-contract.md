# Phase 11 project/revision contract

Phase 11 adds the save/load and immutable-history boundary without changing solver, Vastu, geometry, validation or scoring behavior.

## Project record

A project contains mutable project-level identity metadata and a pointer to the current immutable revision. `current_revision_number` starts at zero.

## Revision record

Each revision contains:

- project and revision identity;
- sequential revision number;
- explicit parent revision ID;
- timezone-aware creation time;
- canonical hashed `PlanDocument`;
- optional selected candidate ID and note;
- content-addressed generated-output references;
- deterministic payload hash.

The `PlanDocument` hash remains the authoritative reproducibility hash for plan content. Revision `payload_hash` covers revision ancestry and revision metadata but intentionally excludes creation time.

## Concurrency

Appending revision N+1 requires the caller to present revision N as `expected_parent_revision_id`. A stale parent fails with a conflict and cannot overwrite history.

## Storage

`SqliteProjectRepository` is the Phase 11 reference/local adapter. Production PostgreSQL/Supabase is still required before the production deployment gate.
