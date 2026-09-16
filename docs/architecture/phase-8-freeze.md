# Phase 8 freeze — architectural geometry builder

Phase 8 converts an accepted Phase 7 rectangular solver result into deterministic canonical floor geometry.

Frozen scope:
- one solver floor per build request;
- solver room rectangles become exact integer-mm `RoomGeometry` polygons;
- orthogonal room boundaries are split into deterministic atomic wall axes;
- shared room boundaries produce one wall axis, not duplicates;
- T-junction endpoints split collinear wall axes deterministically;
- external/internal wall classification derives from buildable-boundary geometry;
- wall thickness/height are mandatory explicit inputs;
- openings are created only from explicit wall-relative requests;
- a basic stair can be created only from an explicit staircase-room request;
- all entity IDs are deterministic UUIDv5 values;
- output includes source-problem/source-planner hashes and its own content hash.

Important limitation:
Phase 7 room rectangles did not account for wall thickness. Phase 8 preserves those rectangles as planning envelopes and does not claim certified clear-room dimensions. Phase 9 must independently validate clearances, reachability, openings and architectural validity.

Not in Phase 8:
- automatic door/window placement;
- wall-face Boolean construction;
- door swing clearance validation;
- circulation validation;
- structural columns;
- multi-floor geometry construction;
- final architectural validity certification;
- CAD/PDF/DWG export.
