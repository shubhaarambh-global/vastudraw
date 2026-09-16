# Phase 9 freeze — independent architectural validation gate

Phase 9 adds a deterministic, fail-closed validation layer after Phase 8 geometry construction.
It does not move rooms, resize rooms, place openings, or repair geometry.

Frozen scope:
- validate plot, buildable, floor, room, and stair polygon topology;
- verify buildable-area containment inside the plot;
- require floor boundary parity with the compiled buildable area;
- verify room containment and reject positive-area room overlap;
- reject tiny room sliver polygons using an explicit caller-supplied threshold;
- reject duplicate entity IDs and duplicate wall geometry;
- reject non-orthogonal/orphan/out-of-boundary walls;
- require exact room-boundary coverage by wall axes (dimension closure);
- compute wall-thickness-adjusted clear room dimensions in doubled millimetres;
- enforce compiled minimum width, depth, and area against those clear dimensions;
- validate opening wall attachment, wall bounds, and overlap;
- require explicit clearance context for hinged swinging doors;
- validate a conservative integer-mm door-swing clearance envelope;
- build a circulation graph from doors/openings and reject unreachable rooms;
- validate stair footprint association and exact riser/floor-height closure;
- retain Clipper2 as the primary integer polygon engine and Shapely/GEOS as the independent verifier;
- emit canonical `ValidationReport` errors, warnings, and informational findings;
- emit deterministic SHA-256 provenance for the validation run.

No Vastu compliance is claimed in Phase 9 because the repository Vastu Specification remains
DRAFT with zero frozen production rules.

Not in Phase 9:
- automatic geometry repair;
- automatic door/window placement;
- structural design;
- code/regulation-specific stair minimums that have not been supplied by an authoritative spec;
- multi-floor egress analysis;
- final Vastu scoring;
- CAD/PDF/DWG export.
