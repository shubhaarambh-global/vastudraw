# ADR-015 — Plot Construction and Edge Identity

## Status
Accepted for Phase 2.

## Decision

1. Canonical plot coordinates remain signed integer millimetres.
2. A manually entered rectangle is constructed axis-aligned in project-local drawing coordinates using the ordered open ring:
   `(origin) → (+X width) → (+Y depth) → (-X width)`.
3. This default rectangle order is counter-clockwise, but downstream direction logic must also support clockwise imported polygons.
4. Plot edge identity is stable and reproducible: edge UUIDs are derived with UUIDv5 from `plot.id` plus the boundary edge index.
5. Phase 2 accepts polygon geometry only when corner coordinates are already established. It does not infer an arbitrary quadrilateral from four side lengths.
6. Survey diagonal/angle/bearing evidence can be represented, but coordinate reconstruction from that evidence is deferred until a dedicated survey-geometry solver is designed and tested.
7. Phase 2 performs basic degeneracy checks only. Full polygon topology/self-intersection validation remains Phase 3.

## Rationale

Stable edge IDs are necessary because roads, setbacks and later regulations reference plot boundaries semantically. Hidden random IDs would damage reproducibility. Separating coordinate establishment from topology validation also keeps Phase 2 narrow and prevents premature dependency on the Phase 3 geometry kernel.
