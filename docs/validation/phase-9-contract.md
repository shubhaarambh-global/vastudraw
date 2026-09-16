# Phase 9 validation contract

`VALIDATOR_VERSION = "1.0.0"`.

## Input

`ArchitecturalValidationRequest` requires:
- plot boundary;
- frozen compiled constraint problem;
- Phase 8 architectural geometry result;
- explicit validation thresholds (`tiny_sliver_area_mm2`, `door_clearance_margin_mm`);
- optional `DoorSwingContext` records, which become mandatory for each hinged swinging door.

No physical dimension threshold is silently invented.

## Output

`ValidationRunResult` contains:
- validator version;
- source problem hash;
- source geometry hash;
- canonical `ValidationReport`;
- deterministic result SHA-256 hash.

A report with any hard finding is invalid. Warnings and informational findings do not make a report
invalid.

## Clear dimensions

For rectangular Phase 8 rooms, wall-axis envelope dimensions are reduced by half of each bounding
wall thickness. Calculations stay exact by using doubled millimetres and quarter-square-millimetres.

## Door clearance

For a hinged door with `IN`/`OUT` swing, the request must specify where the leaf is expected to
sweep (`ROOM` with an adjacent room ID, or `EXTERIOR`). Clearance is checked with a conservative
integer-mm square envelope whose depth equals door width plus the explicit margin.

## Circulation

Only DOOR and OPENING entities participate in circulation. Windows never create graph edges.
Rooms not connected to the exterior node through access openings are hard errors.

## Vastu

This phase emits an informational record that Vastu validity is not claimed while the production
Vastu rule bundle remains empty/DRAFT.
