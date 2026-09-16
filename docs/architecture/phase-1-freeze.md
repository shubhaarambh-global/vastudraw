# Phase 1 Architecture Freeze — Canonical Schema

Status: **PROPOSED UNTIL ACCEPTANCE GATE PASSES**

## Scope

Phase 1 implements only the canonical representation layer:

- signed integer-millimetre coordinates;
- integer square-millimetre areas where an area value is explicitly stored;
- fixed-point integer microdegrees for orientation;
- deterministic conversion/quantization from external units;
- immutable Pydantic canonical models;
- `PlanDocument` schema version `1.0.0`;
- deterministic canonical JSON and SHA-256 content hashing;
- JSON Schema export and generated TypeScript declarations;
- fail-closed schema-version parsing.

Phase 1 intentionally does **not** implement polygon Boolean operations, topology validation, Vastu rules, CP-SAT planning, architectural wall construction, scoring algorithms, or CAD exporters.

## Canonical-unit decisions

1. Authoritative coordinates are signed integer millimetres (`int64` range).
2. Positive dimensions use positive integer millimetres.
3. Orientation is `[0, 360°)` represented as integer microdegrees.
4. External decimal measurements are converted with `Decimal`, never binary `float`.
5. Quantization to millimetres uses deterministic `ROUND_HALF_UP` and records exact input plus rounding delta.
6. Polygon rings are stored open; the first vertex is not repeated at the end.
7. Floor-owned rooms/walls/openings remain nested under their floor and are not duplicated at the document root.

## Hashing contract

The content hash is SHA-256 over UTF-8 canonical JSON with:

- keys sorted lexicographically;
- compact separators;
- `content_hash` excluded from the hashed payload;
- array order preserved because ordering is semantically meaningful.

This is a content-integrity/reproducibility identifier, not a digital signature.

## Schema ownership

Python/Pydantic is authoritative. JSON Schema is generated from Pydantic. TypeScript declarations are generated from the committed JSON Schema. Hand-maintaining a second authoritative frontend geometry model is prohibited.

## Phase 2 entry condition

Phase 1 is frozen only after Python, TypeScript, generated-contract drift, serialization/hash, unit-conversion, and schema-policy tests pass.
