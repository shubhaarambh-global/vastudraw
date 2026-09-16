# Phase 2 Validation Record

## Acceptance criteria

Phase 2 is accepted only when all Phase 0/1 gates remain green and the new tests prove:

- 30 ft × 50 ft converts exactly to 9144 mm × 15240 mm;
- 10 m × 18 m converts exactly to 10000 mm × 18000 mm;
- rectangle boundary and plot-edge ordering are deterministic;
- repeated construction with the same plot ID produces identical edge IDs;
- verified coordinate polygons preserve supplied coordinates;
- four arbitrary side lengths alone are rejected as underdetermined;
- Phase 2 does not silently solve diagonal/angle/bearing survey evidence;
- closure discrepancy is measured and preserved in integer millimetres;
- corner plots can carry multiple roads on distinct edges;
- unknown/duplicate road-edge assignments fail closed;
- road direction is derived from outward normal plus true-North rotation;
- a 13.72° North rotation is stored as exactly 13,720,000 microdegrees;
- clockwise and counter-clockwise plot rings produce correct outward normals;
- compound roads with different edge facings do not receive an invented single direction;
- no Phase 3 geometry or Phase 7 solver dependencies are introduced early.

The user's Windows acceptance run is authoritative for the frozen phase package.
