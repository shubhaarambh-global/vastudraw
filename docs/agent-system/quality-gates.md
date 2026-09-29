# Quality Gates

## Focused
Run tests nearest to the change first.

## Python
- Ruff on changed Python
- focused pytest
- mypy when types/contracts change

## Web
- `pnpm --filter ./apps/web typecheck`
- `pnpm --filter ./apps/web test`
- `pnpm --filter ./apps/web build`

## Repository
- `git diff --check`
- `pnpm validate`

## Live
Only when safe/configured:
- PostgreSQL/Supabase persistence
- production auth
- OpenRouter
- Gemini
- PhonePe/Razorpay

Classify each gate:
- PASS_LOCAL
- PASS_LIVE
- BLOCKED_CREDENTIALS
- BLOCKED_HUMAN_ACTION
- FAIL

Never collapse blocked into passed.
