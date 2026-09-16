# Phase 5 Freeze — Vastu Specification v1.0 Authoring Pipeline

## In scope
- Vastu Specification version constant `1.0.0`;
- repository manifest/source/rule authoring layout;
- immutable rule review metadata;
- source validation and geometry-semantics review flags;
- explicit human reviewer attestations;
- mandatory VASTU_EXPERT approval before production;
- deterministic authoring-content hash;
- FROZEN manifest with exact rule IDs/count/bundle hash;
- fail-closed production release compiler;
- human-readable review packet generation;
- repository specification kept DRAFT with zero real rules until sources/review are supplied.

## Explicitly out of scope
- inventing any Vastu doctrine;
- claiming a rule is expert-reviewed without an actual reviewer;
- CP-SAT integration;
- room constraint compilation;
- CAD/editor/export work.

## Frozen boundary
An LLM can help prepare a draft authoring record or explanation, but it cannot create reviewer attestations, set production approval, or bypass release hash validation.
