# Phase 7 freeze — CP-SAT rectangular planner

Phase 7 introduces the first mathematical layout solver without changing the canonical PlanDocument or Phase 6 compiled-constraint contract.

Frozen scope:
- OR-Tools 9.15.6755;
- single floor;
- axis-aligned rectangular buildable area;
- rectangular room variables;
- explicit solver lattice;
- `NoOverlap2D`;
- exact hard dimension/area/aspect checks on reconstructed mm values;
- bounded search;
- deterministic single-worker configuration;
- explicit notices for unsupported soft objectives;
- fail-closed handling of unsupported hard semantics;
- hashed solver result/provenance.

Not in Phase 7:
- real Vastu optimization;
- multi-floor solving;
- irregular buildable polygons;
- hard adjacency prohibition;
- walls, doors, windows or stairs;
- candidate diversity;
- final architectural validation.
