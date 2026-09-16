# ADR-042 — Vastu production review boundary

## Status

Accepted for Phase 20.

## Decision

Source research and deterministic normalization may advance a rule to the source-verified review stage, but cannot by themselves make it production doctrine.

The existing approval invariant remains unchanged: a production rule requires source validation, geometry-semantics review, and at least one explicit approving attestation from a real reviewer recorded with the `VASTU_EXPERT` role.

Phase 20A therefore uses `IN_REVIEW` / `SOURCE_VERIFIED`, not `FROZEN` / `APPROVED`.

## Rationale

Vastu literature contains variant traditions, alternative placements and interpretation-dependent terminology. Treating a web source or model synthesis as equivalent to human domain review would create false authority. The project remains fail-closed until the explicit review boundary is crossed.
