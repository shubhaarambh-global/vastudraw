# ADR-027 — Architectural geometry builder

## Status
Accepted for Phase 8.

## Decision
Introduce `ai_vastu.architectural_geometry` as the only Phase 8 boundary allowed to translate solver placements into canonical floor geometry.

The builder accepts a `CompiledConstraintProblem`, a feasible `PlannerResult`, explicit floor metadata, and explicit wall/opening/stair inputs. It emits canonical `RoomGeometry`, `Wall`, `Opening`, `Stair` and `Floor` models plus deterministic provenance hashes.

The builder must not invent wall thickness, wall height, opening placement or stair dimensions.

## Why
The solver decides allocation; canonical architectural geometry must be constructed by a deterministic domain layer rather than by OR-Tools objects, the browser, or an LLM.

## Rejected
- writing PlanDocument geometry directly inside the CP-SAT adapter;
- Canvas/Konva coordinates as authoritative geometry;
- defaulting wall thickness or opening positions silently;
- LLM-drawn wall topology.
