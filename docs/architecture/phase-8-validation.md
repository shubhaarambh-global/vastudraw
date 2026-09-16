# Phase 8 validation gate

Acceptance requires:

1. `pnpm validate`
2. `ruff check python apps/api tests`
3. strict `mypy`
4. full `pytest`
5. deterministic geometry smoke run produces the same `Floor` and content hash twice
6. every feasible solver placement becomes an exact room polygon with unchanged coordinates and dimensions
7. wall axes are unique and deterministically identified
8. shared/partial room boundaries do not create duplicate wall axes
9. external/internal wall thicknesses come only from explicit input
10. invalid or overlapping opening requests fail closed
11. stair construction requires an explicit staircase room and stair parameters
12. Phase 8 introduces no CAD/export dependency
13. the Phase 5 Vastu Specification remains DRAFT with zero production rules

The Windows Python 3.12 / Node 24 environment remains the authoritative acceptance environment.
