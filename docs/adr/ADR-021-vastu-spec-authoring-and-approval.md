# ADR-021 — Vastu Specification authoring and approval workflow

## Status
Accepted for Phase 5.

## Decision
Vastu doctrine is authored as versioned repository data, separate from runtime code and separate from LLM prompts. A rule cannot enter production unless its typed `VastuRule` is `FROZEN` **and** its typed `RuleReview` is `APPROVED`.

`APPROVED` requires source validation, geometry-semantics review, and at least one explicit human `VASTU_EXPERT` approval attestation. Reviewer identity and timestamp are immutable data. The system provides no automatic or LLM-driven promotion operation.

## Consequences
- unsourced rules remain DRAFT;
- approved rules are auditable;
- expert review is machine-enforced at release time;
- rule interpretation and geometry semantics remain reviewable independently.
