# ADR-019 — Vastu Rule Representation and Lifecycle

## Status
Accepted for Phase 4.

## Decision
Vastu knowledge is represented as immutable, typed `VastuRule` records rather than application code or LLM prompts.

Every rule has a stable ID, semantic version, Vastu specification version, subject selector, explicit geometry semantic, typed predicate, hard/soft classification, severity, weight, precedence, provenance references, exceptions, lifecycle state, and explanation template.

Lifecycle is exactly:

`DRAFT → REVIEWED → FROZEN → RETIRED`

Only `FROZEN` rules may enter a production rule bundle. `REVIEWED` and `FROZEN` rules require source references. Phase 4 contains no production Vastu rule catalog.

## Rationale
This makes Vastu behavior auditable, source-backed, versioned, deterministic, testable, and independent from the LLM.

## Consequences
Changing Vastu doctrine requires a versioned rule change and review process. The runtime cannot invent or mutate production rules.
