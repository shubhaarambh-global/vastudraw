# Phase 24B — Confirmed Requirements → Deterministic Generator

Phase 24B binds Phase 24A's human-confirmed requirements to the repository's
actual Phase 16 generation contract.

The exact inspected contract is:

`generate_architectural_plan(request: ArchitecturalGenerationRequest)
 -> ArchitecturalGenerationResult`

## What 24B does

1. Loads an immutable confirmed requirements draft.
2. Verifies authenticated user/project identity.
3. Enforces the Phase 23 server-side billing entitlement.
4. Requires explicit acceptance of versioned architectural generation defaults.
5. Compiles a rectangular integer-mm `ArchitecturalGenerationRequest`.
6. Validates that request using the existing authoritative Pydantic model.
7. Calls the existing deterministic `generate_architectural_plan`.
8. Consumes the one-time free generation only if disposition is `ACCEPTED`.
9. Preserves paid-project regeneration semantics.

## Deliberate fail-closed boundary

The inspected `ArchitecturalGenerationRequest` does not carry true-North,
road-side/facing, or an explicit Vastu evaluation object. The inspected result
contains constraint/planner/geometry/validation output but does not contain the
project revision or scoring layer.

Therefore Phase 24B does NOT pretend that:
- North/facing has already affected the Phase 16 planner;
- the generated plan has already passed the frozen Vastu evaluator;
- the generation result has already been converted into the canonical
  `PlanDocument`;
- a project revision has already been persisted.

`scripts/inspect-phase24-final-contracts.py` exports the exact PlanDocument,
Vastu, scoring, project, and API-route contracts needed to complete that final
binding safely.

This remains part of roadmap Phase 24.
