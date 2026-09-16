# ADR-041 — Production MVP Release Gate

## Status
Accepted for Phase 15.

## Decision
Production promotion is a separate fail-closed decision from ordinary engineering CI.
`pnpm mvp:check` verifies that the release-readiness evaluator is deterministic and that
the repository's known blocker set is explicit. `pnpm mvp:release` is the promotion gate
and exits non-zero whenever any release blocker remains.

The gate must not convert missing governance, security, persistence or product workflow
capabilities into warnings merely to produce a green release badge.

## Current consequence
The public MVP is blocked because Vastu Specification v1 is still DRAFT with zero frozen
production rules, and because authentication/authorization, the planned production
persistence adapter and end-to-end generation/web/API workflow are not yet implemented.
The DWG pathway itself satisfies the MVP scope because it is present and fail-closed; a
provider runtime is still required before actual DWG export may be enabled.
