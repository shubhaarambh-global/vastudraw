# Phase 9 validation

Authoritative acceptance environment: Windows 11, Python 3.12, Node.js 24.

Run:

```powershell
pnpm validate
ruff check python apps/api tests
mypy
pytest
```

The Phase 9 smoke command is included in `pnpm validate` as `validation:check`.

Acceptance requires:
- deterministic validation output and content hash;
- no Python lint/type failures;
- full test-suite pass;
- no new CAD/export dependency;
- PlanDocument schema version remains `1.0.0`;
- Vastu Specification remains DRAFT/empty until real expert-reviewed rules are supplied.
