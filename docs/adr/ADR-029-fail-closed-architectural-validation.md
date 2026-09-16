# ADR-029 — Fail-closed architectural validation

## Status
Accepted for Phase 9.

## Decision
A generated floor is not considered architecturally valid merely because the solver found a
feasible placement or the geometry builder emitted canonical entities. Phase 9 runs a separate
validation gate and returns `ValidationReport.valid = false` whenever a hard invariant fails.

The validator is read-only. It never repairs or silently changes authoritative geometry.

Critical polygon checks use `VerifiedGeometryKernel`: Clipper2 performs deterministic integer-mm
polygon operations and Shapely/GEOS independently checks topology and operation parity.

## Consequences
- solver feasibility and architectural validity remain separate claims;
- geometry-kernel disagreement cannot be silently ignored;
- downstream scoring/export must consume only a passing validation report;
- validation findings are deterministic, typed, and machine-readable.
