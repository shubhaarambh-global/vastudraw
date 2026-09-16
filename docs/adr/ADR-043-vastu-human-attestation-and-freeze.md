# ADR-043 — Human Vastu attestation and deterministic production freeze

## Decision

The first production Vastu bundle is created only after an explicit human reviewer action. The system does not infer approval from account ownership, architecture credentials, source availability, or AI output.

The approval command requires a stable reviewer ID and an explicit confirmation token. It records a timezone-aware `VASTU_EXPERT` approval attestation in every approved rule record and marks geometry semantics reviewed.

The freeze command is separate from approval. It deterministically compiles the typed FROZEN rules through the existing `SourceRegistry` and `compile_rule_bundle()` path, then pins the computed SHA-256 in the manifest. The production bundle and release record are serialized as audit artifacts.

## v1.0 interpretation decisions

For the four Phase 20 rules, the approving reviewer accepts the current eight-sector direction model, room-centroid semantics, SE-only primary kitchen rule, S/SW master-bedroom predicate, separate bath/toilet handling, and SOFT MVP weights/severities.

## Consequences

- No Vastu expert identity is fabricated by code or AI.
- Re-running approval for the same reviewer is idempotent.
- A rejection attestation blocks approval.
- The production hash is derived, not entered manually.
- Any future change to a frozen rule necessarily changes the bundle hash and requires a new reviewed release process.
