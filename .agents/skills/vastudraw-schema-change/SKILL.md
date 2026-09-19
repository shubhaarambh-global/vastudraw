---
name: vastudraw-schema-change
description: >-
  Use whenever changing Vastudraw PlanDocument models, plan_schema, contracts,
  enums, JSON schema, content hashes, serialization, migrations, API contract
  shapes, floor/stair/opening models, or persisted canonical geometry. Enforces
  versioning, migrations, schema regeneration, and compatibility testing.
---

# Vastudraw Schema Change Discipline

Use this skill before modifying any canonical or persisted contract.

## Inspect first

Before changing schema:

1. Identify current schema version.
2. Find all model definitions.
3. Find JSON-schema generation code.
4. Find migrations/versioning code.
5. Find hash/canonicalization code.
6. Find API consumers.
7. Find frontend/generated types where applicable.
8. Find fixtures and serialization tests.

Do not change a canonical model in isolation.

## Versioning

If a persisted/public schema shape changes:

- determine whether the schema version must increment;
- add an explicit migration from the prior supported version;
- preserve backward parsing where required;
- update generated schema artifacts;
- update fixtures/tests.

Do not silently reinterpret an old field with new semantics.

## Content hash integrity

Changes that affect canonical serialized content may affect content hashes.

Verify:

- canonical dump ordering;
- exclusions such as `content_hash`;
- UUID/string serialization;
- enum serialization;
- nested tuple/list normalization;
- migration followed by hash recomputation where required.

Never hard-code a hash to satisfy a test.

## Strict Pydantic behavior

Be aware of differences between:

- `model_validate`;
- `model_validate_json`;
- strict Python-mode validation;
- JSON coercion of UUIDs/enums/lists.

Use the canonical parsing route already established by the repository.

## PlanDocument authority

Schema changes must not weaken the rule that `PlanDocument` is authoritative
geometry.

For geometry-bearing fields such as:

- floors;
- rooms;
- purposeful site spaces;
- walls;
- openings;
- stairs;
- fixtures;
- furniture;

ensure new fields have deterministic semantics.

## Required validation

Run relevant:

- plan-schema tests;
- versioning/migration tests;
- export/import tests;
- content-hash tests;
- API contract tests;
- generation tests that emit PlanDocument;
- frontend/generated contract checks if affected;
- Ruff;
- mypy.

Regenerate committed JSON schema when the repository expects it.

## Backward compatibility

Do not break already-supported documents without an explicit architectural
decision.

When backward compatibility cannot be preserved, document:

- affected versions;
- migration path;
- rationale;
- API impact;
- persistence impact;
- rollout requirements.

Record all schema decisions in `docs/CURRENT_HANDOFF.md`.
