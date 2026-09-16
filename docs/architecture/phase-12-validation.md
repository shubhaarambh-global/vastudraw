# Phase 12 validation gate

The authoritative user-environment gate is:

```powershell
pnpm validate
ruff check python apps/api tests scripts
mypy
pytest
```

Frontend acceptance additionally requires:

- Next.js production build succeeds;
- editor TypeScript strict typecheck succeeds;
- native Node tests prove +Y-up transform, anchored zoom, deterministic fit/snap, undo/redo and integer-mm command rejection;
- existing Python solver/geometry/validation/scoring/project gates remain green.
