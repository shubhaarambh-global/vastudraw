# Phase 15 Validation

Run:

```powershell
pnpm validate
ruff check python apps/api tests scripts
mypy
pytest
```

The ordinary validation gate is expected to pass while reporting the current public-MVP
release disposition as `BLOCKED`. To exercise the actual production promotion gate run:

```powershell
pnpm mvp:release
```

That command is intentionally expected to exit non-zero until all blockers are resolved.
Do not put `mvp:release` inside ordinary CI while the repository is knowingly incomplete.
