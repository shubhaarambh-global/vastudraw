# ADR-026 — Solver lattice and reproducibility

## Status
Accepted for Phase 7.

## Decision
Canonical geometry remains integer millimetres. CP-SAT searches on an explicit integer lattice controlled by `solver_step_mm`.

A solver coordinate `k` maps to canonical geometry as:

`coordinate_mm = buildable_origin_mm + k * solver_step_mm`

Hard minimum dimensions and areas are applied against the reconstructed millimetre values, so coarse search cannot produce a room smaller than the user requirement. The unused remainder at the maximum buildable edge is allowed when the buildable dimension is not divisible by the solver step.

Every run records:
- OR-Tools version;
- solver model version;
- input constraint-problem hash;
- solver step;
- time limit;
- conflict limit;
- random seed; and
- worker count.

`num_search_workers` is fixed to 1 and a fixed decision strategy is used for Phase 7 reproducibility. A time-limited `FEASIBLE` result is valid but not claimed to be cross-machine byte-identical; golden acceptance cases are required to reach `OPTIMAL`.
