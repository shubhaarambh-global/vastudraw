# Phase 16 — Deterministic Architectural Generation API

Phase 16 exposes the already-validated deterministic planning chain as a product API workflow:

1. compile explicit room requirements and buildable geometry;
2. solve the single-floor rectangular problem with OR-Tools CP-SAT;
3. build canonical architectural room/wall geometry;
4. independently validate the generated geometry;
5. return a canonical hashed generation result.

The endpoint is `POST /generation/architectural`.

## Important boundary

This phase does **not** invent or apply production Vastu doctrine. Vastu Specification v1 remains DRAFT and empty, so the generation endpoint is architectural-only until the reviewed rule bundle is frozen and cryptographically pinned.

No new runtime dependency is introduced.

## Draft-candidate validation

The geometry builder does not invent doors or windows. A request with no explicit openings therefore returns a deterministic draft candidate that independent validation marks `REJECTED` for circulation. This is intentional: the API exposes the validation evidence rather than silently adding architectural decisions.
