# ADR-035 — Browser editor coordinates are non-authoritative

## Status
Accepted for Phase 12.

## Decision
The browser editor consumes the canonical `PlanDocument` and renders it through an explicit world-mm to screen-pixel transform. Canvas pixels, drag offsets and Konva node positions are never canonical geometry.

All edit requests are represented as exact integer-mm commands tied to a base revision. The existing backend solver, geometry builder and validation gate remain the only path to a replacement authoritative revision.

The editor also rejects fractional and JavaScript-unsafe integer edit values instead of silently rounding or losing integer precision.

## Consequences
This prevents zoom level, device pixel ratio, browser floating-point interaction and canvas transforms from corrupting the millimetre model. It also means some edits remain pending previews until the backend produces a validated revision.
