# ADR-046 — Phase 24 canonical generation commit

## Status

Accepted.

## Decision

Commercial generation is an orchestration layer around existing authoritative
subsystems. It does not move billing into the legacy Phase 16 engineering
endpoint and does not create a second geometry engine.

The order is:

1. authenticate and verify project ownership;
2. load immutable confirmed requirements;
3. authorize entitlement;
4. compile and execute the existing deterministic generator;
5. require ACCEPTED geometry and validation output;
6. load and verify the frozen production Vastu v1 RuleBundle;
7. derive deterministic room-centroid sector facts in confirmed true-North context;
8. run the existing Vastu evaluator;
9. run the existing scoring selector;
10. construct the canonical PlanDocument;
11. append an immutable project revision;
12. only then record successful generation in billing;
13. return the persisted revision and Editor handoff.

Revision IDs are deterministic from project, draft, generation identity, and
frozen Vastu bundle hash. A retry therefore cannot create a second revision for
the same accepted generation. If the revision already exists, it is retrieved
and the billing success transition can safely be retried.

The inspected Phase 16 generator is single-floor. Multi-floor confirmed briefs
fail closed in this MVP rather than being partially generated.
