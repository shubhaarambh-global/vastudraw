# Phase 5 Validation Gate

Required checks:

```text
pnpm validate
ruff check python apps/api tests
mypy
pytest
python scripts/check-vastu-spec.py
```

Acceptance invariants:
- repository Vastu Specification v1.0 is valid but DRAFT;
- repository contains zero production Vastu rule JSON files;
- APPROVED review requires source validation, geometry review and a VASTU_EXPERT approval;
- a FROZEN rule cannot carry a non-approved review;
- a FROZEN specification cannot be empty;
- production release requires FROZEN manifest + FROZEN/APPROVED rules;
- production release bundle hash must equal the frozen manifest hash;
- authoring and release hashes are deterministic;
- PlanDocument schema remains 1.0.0;
- OR-Tools, ezdxf and ReportLab remain absent.
