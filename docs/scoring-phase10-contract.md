# Phase 10 scoring contract

Input is a `ScoringRequest` containing one compiled constraint problem, explicit `ScoringConfig`, and a
non-empty tuple of `ScoringCandidate` objects.

Each candidate must carry:
- a feasible hashed `PlannerResult` for the same problem;
- a hashed `ArchitecturalGeometryResult` chained to that planner result;
- a hashed, valid `ValidationRunResult` chained to that geometry result.

Output is a hashed `ScoringRunResult` containing selected ranked alternatives, excluded alternatives
with machine-readable reason codes, and scoring notices.

Current score mode is `ARCHITECTURAL_SOFT_CONSTRAINTS_V1`. It is intentionally not a Vastu score.
