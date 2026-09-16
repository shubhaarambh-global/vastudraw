# Phase 8 architectural geometry contract

Version: `1.0.0`

Input:
- frozen Phase 6 compiled constraint problem;
- feasible Phase 7 planner result;
- floor ID/name/elevation/floor-to-floor height;
- explicit external/internal wall thickness and wall height;
- optional explicit opening requests;
- optional explicit stair requests.

Output:
- one canonical `Floor`;
- exact solver-room polygons;
- deterministic wall axes;
- explicit openings/stairs only where requested;
- provenance notice that wall thickness was not part of the Phase 7 solve;
- SHA-256 hashes for source problem, source planner result and Phase 8 output.

Fail closed when:
- solver result is not feasible;
- placements do not exactly match compiled room instances;
- more than one solver floor is present;
- a room edge is non-orthogonal;
- an opening references a missing wall or extends outside it;
- openings overlap on the same wall;
- a stair references a non-staircase room.
