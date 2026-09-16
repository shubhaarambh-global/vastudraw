# Phase 7 CP-SAT planner contract

## Input
`CompiledConstraintProblem` from Phase 6 plus explicit `PlannerConfig`.

## Output
`PlannerResult` containing exact integer-mm rectangular room placements, solver provenance, objective evidence, explicit unsupported-soft notices and a canonical content hash.

## Authoritative boundary
The solver does not create walls, openings, CAD entities or final `RoomGeometry`. Phase 8 converts accepted placements into architectural geometry and independently validates it.

## Supported hard constraints
- rectangular buildable-area containment;
- available single-floor domain;
- minimum / maximum width and depth;
- minimum / maximum area;
- aspect ratio;
- global room non-overlap.

Hard adjacency prohibition is intentionally rejected in Phase 7 rather than ignored.

## Supported soft objectives
- preferred width/depth deviation in millimetres;
- adjacency preference against a target room type, including maximum gap and minimum shared projection when supplied.

Preferred area, daylight, ventilation, privacy and soft adjacency avoidance are retained in the compiled problem but produce explicit `SOFT_OBJECTIVE_NOT_YET_OPTIMIZED` notices in Phase 7.

## Vastu
The repository Vastu Specification remains DRAFT with zero production rules. Therefore Phase 7 performs no Vastu optimization and makes no Vastu-compliance claim.
