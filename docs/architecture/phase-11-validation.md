# Phase 11 validation gate

Authoritative acceptance commands:

```text
pnpm validate
ruff check python apps/api tests scripts
mypy
pytest
```

Acceptance requires all inherited phase gates plus the project-revision persistence smoke, strict Python checks and complete test suite.
