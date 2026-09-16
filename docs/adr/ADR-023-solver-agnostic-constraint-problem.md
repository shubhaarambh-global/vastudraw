# ADR-023 — Solver-agnostic constraint problem

## Status
Accepted for Phase 6.

## Decision
Room requirements compile into an immutable, deterministic `CompiledConstraintProblem` before any optimizer is invoked. The model separates `hard_constraints` from `soft_constraints`, expands room quantities into stable room-instance IDs, carries the verified buildable area and floor set, and records a canonical SHA-256 content hash.

No OR-Tools classes, variable handles, protobufs, or solver-specific expressions may cross this boundary.

## Rationale
Keeping the compiler solver-agnostic makes requirement interpretation independently testable, allows future solver replacement, and prevents optimization implementation details from becoming part of the canonical domain model.

## Consequences
Phase 7 must translate this problem into CP-SAT. It may not reinterpret user requirements independently.
