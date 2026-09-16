# ADR-018 — Independent geometry verification

Status: Accepted for Phase 3

## Decision

Shapely/GEOS is the independent topology verifier. It does not own or rewrite canonical geometry.

For Boolean operations the verified facade compares Clipper2 output against an independently computed Shapely result and fails closed on material disagreement. For offsets, Phase 3 validates output topology but does not demand exact cross-engine parity because offset rounding semantics differ between integer Clipper2 and floating GEOS.

A later validation phase may strengthen this matrix as golden cases accumulate.
