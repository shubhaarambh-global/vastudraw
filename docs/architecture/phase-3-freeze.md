# Phase 3 Freeze — Geometry Kernel

Phase 3 adds deterministic polygon infrastructure only.

Included:
- Clipper2 primary kernel through a private `pyclipr` adapter.
- Shapely/GEOS independent topology verification.
- integer-mm Boolean union/intersection/difference/XOR.
- integer-mm polygon offsetting.
- containment.
- exact doubled-area calculation.
- deterministic ring normalization and result ordering.
- fail-closed cross-engine disagreement errors.
- 2,500 randomized rectangle property examples plus deterministic unit tests.

Excluded:
- Vastu rules.
- CP-SAT room placement.
- wall construction.
- CAD export.
- building regulation logic.
