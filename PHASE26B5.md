# AI Vastu Architect — Phase 26B.5

Existing Plan Intake + Provisional Vastu Audit.

Apply from the repository root:

```powershell
python .\scripts\apply-phase26b5.py
```

Then normalize and validate:

```powershell
python -m ruff format python apps/api tests scripts
python -m ruff check python apps/api tests scripts --fix
pnpm --filter @ai-vastu/web exec prettier --write .
pnpm --filter @ai-vastu/web exec eslint . --fix
mypy
python -m pytest tests\plan_intake tests\test_phase26b5_policy.py -q
pnpm phase26b5:check
pnpm --filter @ai-vastu/web typecheck
pnpm --filter @ai-vastu/web test
```

If all focused checks pass, run `pnpm validate`.

Do not delete the validated Phase 26A/26B working-tree changes. This overlay
is built on top of that exact snapshot.
