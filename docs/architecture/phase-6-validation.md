# Phase 6 validation

Acceptance requires:

```text
pnpm validate
ruff check python apps/api tests
mypy
pytest
python scripts/check-constraint-compiler.py
python scripts/check-vastu-spec.py
```

Required invariants include deterministic compilation under input reordering, stable quantity expansion, hard/soft separation, no invented assumptions, conflict rejection, exact capacity preflight, and no solver/CAD dependencies.
