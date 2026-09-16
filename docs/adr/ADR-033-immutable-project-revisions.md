# ADR-033 — Immutable project revisions

## Decision

A project is mutable only through an append-only sequence of immutable revisions. Every revision stores one canonical, hashed `PlanDocument`, an explicit parent revision, optional source-candidate identity, and content-addressed output references.

A new revision may be appended only when `expected_parent_revision_id` equals the project's current revision. This optimistic concurrency guard prevents stale browser/editor sessions from silently overwriting newer work.

There is no update or delete operation for revision content in Phase 11.

## Rationale

The product specification requires users to never lose previous plans and requires generation reproducibility. Append-only history makes comparison, rollback, audit and later collaboration tractable without mutating canonical historical geometry.
