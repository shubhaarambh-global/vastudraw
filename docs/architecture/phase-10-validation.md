# Phase 10 validation gate

Phase 10 acceptance requires the complete inherited validation chain plus the scoring smoke.

Required commands in the authoritative Windows Python 3.12 / Node 24 environment:

```powershell
pnpm validate
ruff check python apps/api tests scripts
mypy
pytest
```

`pnpm scoring:check` must prove:
- deterministic repeated scoring;
- two geometrically distinct validated alternatives survive selection;
- architectural score mode is explicit;
- result hashes are stable.

The full pytest suite additionally checks hash-chain failure, duplicate removal, deterministic ranking,
and Phase 10 vendor-boundary policy.
