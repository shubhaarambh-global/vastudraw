# ADR-025 — OR-Tools CP-SAT rectangular planner

## Status
Accepted for Phase 7.

## Decision
Use Google OR-Tools CP-SAT as the first mathematical room-placement solver, behind the `ai_vastu.solver` boundary.

Phase 7 models only:
- one floor;
- an axis-aligned rectangular buildable area;
- rectangular rooms;
- integer solver-lattice coordinates;
- containment;
- minimum/maximum dimensions;
- minimum/maximum area;
- aspect-ratio constraints;
- two-dimensional non-overlap;
- preferred dimensions; and
- basic room-type adjacency preference.

Unsupported hard semantics fail closed. Soft semantics not yet optimized are returned as explicit planner notices.

## Why
CP-SAT natively supports integer variables, multiplication equalities, interval variables and `NoOverlap2D`, which align with the project's deterministic integer-geometry requirements.

## Rejected
- LLM-authored placement: non-deterministic and geometrically unauthoritative.
- random packing: unsuitable for reproducibility and hard constraints.
- direct vendor types in domain contracts: would couple the architecture to OR-Tools.
