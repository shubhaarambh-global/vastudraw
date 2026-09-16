# Phase 4 Freeze — Vastu Rule Framework

Phase 4 freezes the infrastructure for Vastu knowledge without freezing Vastu doctrine itself.

## In scope
- immutable typed Vastu rules;
- DRAFT / REVIEWED / FROZEN / RETIRED lifecycle;
- explicit geometry semantics;
- numeric, enum, and boolean predicates;
- source registry and source references;
- deterministic production rule-bundle compilation;
- SHA-256 bundle hashing;
- hard-rule contradiction detection;
- evidence-backed fact evaluation;
- exact area-overlap fact extraction using Phase 3 geometry;
- synthetic tests only.

## Explicitly out of scope
- real kitchen, puja, bedroom, entrance, toilet, staircase, Brahmasthan, Mandala, or other Vastu doctrine;
- Vastu Specification v1.0 content;
- expert review/approval;
- CP-SAT integration;
- scoring policy beyond per-rule earned/raw weight evidence;
- CAD/editor/export work.

## Frozen boundaries
The LLM does not author runtime rules. Production evaluation consumes only FROZEN rules from a deterministic compiled bundle.
