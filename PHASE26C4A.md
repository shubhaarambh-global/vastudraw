# Phase 26C.4A — Architectural Planning Foundation

Built against checkpoint `aa168c2` (`phase26c3-validated`).

This phase corrects the failure mode exposed by the first live 30×50 ft test:
solver-feasible rectangle packing was being presented as if it were a residential plan.

## What changes

- Adds a documented automatic occupied-room planning target.
- Caps automatic expansion by room role so parking/service spaces cannot absorb residual area.
- Optimizes preferred room area when Phase 26A supplies one.
- Penalizes empty area inside the occupied-room bounding box.
- Adds deterministic residential topology preferences.
- Adds a system circulation lobby for 2+ bedroom V1 plans when no lobby/corridor/foyer was requested.
- Maps confirmed true-world road and entrance directions into the local rectangular solver frame.
- Hard-pins parking/garage envelopes to the confirmed road-side boundary.
- Hard-pins the deterministic entry room to the confirmed entrance-facing boundary.
- Auto-generated exterior access doors must be placed on that entrance boundary.
- Candidate explanations disclose room-envelope utilization.
- The UI stops presenting search-strategy names as if they were proven architectural qualities.

## Important scope boundary

The automatic planning target is not permissible built-up area, FAR/FSI, setback compliance,
or a regulatory entitlement. Regulations remain a separate future input.

This phase does not claim full architectural scoring. Furniture feasibility, true daylight/
ventilation metrics, privacy sightlines, plumbing optimization and the rebuilt architecture
score remain later work.

Structural design remains V2.
