# Phase 7 validation gate

Acceptance requires:

1. `pnpm validate`
2. `ruff check python apps/api tests`
3. strict `mypy`
4. full `pytest`
5. deterministic CP-SAT smoke run reaches OPTIMAL
6. all emitted room rectangles remain inside the buildable rectangle
7. no pair of emitted room rectangles has positive overlap area
8. same input/config produces the same optimal placements and result hash in the acceptance environment
9. unsupported hard semantics fail closed
10. Vastu Specification remains DRAFT with zero production rules

The Windows Python 3.12 / Node 24 environment is the authoritative native acceptance environment for this phase.
