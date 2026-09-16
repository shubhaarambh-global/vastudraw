# ADR-030 — Exact clear dimensions and circulation graph

## Status
Accepted for Phase 9.

## Decision
Phase 8 room polygons are wall-axis planning envelopes. Phase 9 therefore computes clear room
width/depth after wall thickness rather than treating the planning envelope as usable clear space.

To preserve exactness with odd wall thicknesses such as 115 mm, clear dimensions are represented
internally in doubled millimetres:

`clear_width_2mm = 2 * envelope_width_mm - left_wall_mm - right_wall_mm`

Clear area is compared in quarter-square-millimetre units without floating-point rounding.

Circulation is represented as a graph:
- rooms are graph nodes;
- exterior is a distinguished node;
- DOOR and OPENING entities create edges only through their attached wall;
- an external-wall access opening connects its adjacent room to exterior;
- internal access openings connect rooms sharing that wall;
- every room must be reachable from exterior.

Swinging doors require explicit clearance context. The validator uses a conservative integer-mm
square sweep envelope, including the caller-supplied clearance margin. This may reject marginal
layouts rather than falsely certify clearance.
