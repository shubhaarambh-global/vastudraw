# ADR-020 — Vastu Rule Bundle, Provenance, and Deterministic Compilation

## Status
Accepted for Phase 4.

## Decision
Rules compile into an immutable `RuleBundle` with deterministic ordering and SHA-256 content hashing.

Compilation fails closed when:
- a source reference cannot be resolved;
- rule IDs are duplicated;
- a rule targets a different Vastu specification version;
- equal-precedence hard rules on the same subject/semantic/metric are mutually contradictory.

Production compilation excludes DRAFT, REVIEWED, and RETIRED rules. Only sources actually referenced by selected rules enter the bundle.

## Rationale
A generation run must be able to record exactly which reviewed Vastu knowledge influenced it. Deterministic bundle hashing gives reproducible provenance.

## Consequences
Rule bundles can be pinned to generation metadata in later phases. Rule authors cannot bypass source validation or contradiction checks.
