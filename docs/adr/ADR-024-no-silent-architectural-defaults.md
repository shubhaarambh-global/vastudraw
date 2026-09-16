# ADR-024 — No silent architectural defaults

## Status
Accepted for Phase 6.

## Decision
The Phase 6 compiler does not inject room sizes, adjacency weights, floor preferences, or assumptions that were absent from the normalized input. Any documented default applied upstream must already appear as an explicit `Assumption` and as explicit values in `RoomRequirement`.

Soft adjacency avoidance is preserved with an explicit `UNSPECIFIED_IN_REQUIREMENT` weight marker because the current canonical schema does not provide a penalty weight for `AdjacencyProhibition(hard=False)`.

## Rationale
Inventing architectural values inside the compiler would violate the product assumption policy and make generated plans difficult to explain or reproduce.
