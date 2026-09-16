# Phase 14 validation gate

Authoritative Windows acceptance:

```powershell
pnpm validate
ruff check python apps/api tests scripts
mypy
pytest
```

Phase 14 additionally requires:

- provider registry smoke passes;
- no DWG/proprietary runtime binary is bundled;
- no LibreDWG production import is introduced;
- R2018 target is explicit;
- unqualified/test backends fail closed;
- qualification report hash is deterministic;
- backend id/version and DrawingScene hash are bound into the gate;
- actual production enablement remains false until a real licensed backend and external CAD round-trip evidence are supplied.
