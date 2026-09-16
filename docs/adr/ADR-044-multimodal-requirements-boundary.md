# ADR-044 — Multimodal requirements interpretation boundary

## Status

Accepted for Phase 24A.

## Decision

Multimodal AI is an interpretation layer only.

It may:
- parse natural-language client briefs;
- inspect reference JPG/PNG/PDF uploads;
- propose dimensions, orientation, room requirements and preferences;
- flag ambiguity;
- ask follow-up questions.

It may not:
- author authoritative wall/room coordinates;
- silently convert uncertain image measurements into canonical geometry;
- override deterministic Vastu rules;
- bypass architectural validation;
- bypass billing entitlement checks;
- certify statutory or structural compliance.

Every AI-derived planning input is stored as a draft. A human must submit a
separate confirmed-requirements object before the deterministic generation
adapter may use it.

The final Phase 24B adapter must target the repository's actual frozen generation
contract, not a guessed duplicate model.

## Rationale

This preserves the project's 1 mm canonical geometry boundary and keeps
non-deterministic multimodal interpretation outside the authoritative planner.
