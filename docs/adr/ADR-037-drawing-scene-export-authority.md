# ADR-037 — DrawingScene export authority

Status: Accepted for Phase 13

## Context

The same canonical plan geometry must drive browser display, JPG, vector PDF, DXF and later DWG without format-specific geometry drift.

## Decision

Phase 13 materializes the previously accepted DrawingScene abstraction as a deterministic, exporter-independent scene derived only from `PlanDocument`.

The scene:

- remains bound to project ID, revision ID and floor ID;
- records the source canonical PlanDocument SHA-256 hash;
- stores integer-mm semantic plan entities rather than raster pixels or exporter-native objects;
- has its own canonical SHA-256 scene hash;
- is the only input accepted by the JPG, PDF and DXF renderer adapters.

Format adapters may derive display coordinates, wall-gap segments, text placement and page transforms, but they may not mutate canonical geometry.

## Consequences

A format-specific exporter cannot silently invent or alter plan dimensions. Any later DWG backend must consume the same DrawingScene or explicitly supersede this ADR.
