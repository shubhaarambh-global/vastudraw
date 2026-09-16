# Phase 6 freeze — Room requirements and architectural constraint compiler

Phase 6 freezes the solver-agnostic contract between normalized architectural requirements and the future optimization engine.

Accepted boundaries:

- `RoomRequirement` remains the canonical normalized room request.
- quantity expansion uses deterministic UUIDv5 room-instance identities;
- hard and soft constraints are different typed collections;
- no OR-Tools dependency is present;
- no hidden architectural defaults are applied;
- exact preflight checks fail closed on contradictions and provable infeasibility;
- compiled problems are immutable and content-hashed;
- Vastu Specification v1.0 remains DRAFT with zero production rules.
