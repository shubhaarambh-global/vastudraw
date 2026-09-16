# ADR-022 — Frozen specification release manifest

## Status
Accepted for Phase 5.

## Decision
A production Vastu Specification release is fail-closed and hash-addressed. A FROZEN manifest lists the exact sorted rule IDs, exact production rule count, and the expected deterministic Phase 4 rule-bundle SHA-256.

Release compilation recomputes the rule bundle and refuses release if its hash differs. A separate release hash binds the authoring-content hash, rule-bundle hash, rule count, specification version and timezone-aware release timestamp.

## Consequences
Runtime code can identify exactly which reviewed rule material produced a plan, and content edits cannot silently change an already-frozen release.
