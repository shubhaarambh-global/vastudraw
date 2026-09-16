# ADR-017 — Primary integer polygon kernel

Status: Accepted for Phase 3

## Decision

Canonical polygon construction and Boolean/offset operations use Clipper2 through the `pyclipr` adapter. Domain code imports only `ai_vastu.geometry`; no vendor geometry type may escape the adapter.

Canonical coordinates remain integer millimetres. `pyclipr.scaleFactor` is fixed to `1`, preventing a second hidden unit system.

## Rationale

Clipper2 is designed around robust integer polygon operations. `pyclipr` exposes Clipper2 to Python and currently supports Python 3.12. The wrapper is intentionally isolated because its maintenance/API surface is smaller than Clipper2 itself and may be replaced later without changing domain code.

## Exact areas

Integer vertices can enclose half-square-millimetre areas. Therefore the geometry core exposes exact `area2` (twice area in mm²) rather than silently rounding to integer mm².
