# Phase 2 Freeze — Plot + Orientation Engine

Phase 2 freezes deterministic plot establishment and orientation semantics. It does not introduce polygon Boolean operations, setbacks, room planning, Vastu rule content or CAD generation.

## Frozen capabilities

- exact rectangular plot construction from mm/cm/m/in/ft input;
- deterministic local plot origin and boundary ordering;
- stable UUIDv5 plot-edge identity;
- coordinate-defined polygon plots;
- fail-closed irregular quadrilateral handling when only four side lengths are supplied;
- explicit survey closure discrepancy metadata;
- whole-edge road/access assignments, including corner plots;
- exact true-North rotation in integer microdegrees;
- drawing-bearing → true-bearing conversion;
- outward-normal edge facing analysis;
- deterministic 8-way derived direction classification;
- road-facing analysis that refuses to invent a single direction for non-uniform compound road edges.

## Explicitly deferred

- self-intersection and complete topology validation (Phase 3);
- polygon offset/setback generation (Phase 3);
- survey reconstruction from lengths + diagonals/angles/bearings;
- Vastu sectors/rules;
- building regulations;
- CP-SAT planning;
- architectural walls/openings;
- exports.

## Schema stability

`PlanDocument.schema_version` remains `1.0.0`. Phase 2 uses Phase 1 canonical fields and adds domain services rather than duplicating geometry or changing the public document representation.
