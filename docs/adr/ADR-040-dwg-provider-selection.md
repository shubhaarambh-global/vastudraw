# ADR-040 — Initial DWG provider selection

## Decision

Use ODA Drawings SDK as the preferred production integration candidate for modern DWG, subject to licensing and our own round-trip qualification. Do not use GNU LibreDWG as the production R2018 writer.

## Evidence reviewed 2026-09-14

- ODA Drawings SDK documents creating new DWG files, editing standard objects and saving supported DWG versions including AC1032-era output.
- ODA publishes Python wrapper availability for Drawings SDK under applicable membership.
- GNU LibreDWG 0.13.4 documents useful write support only through R2000, with later writing still incomplete/experimental.

## Rationale

The product requires genuine modern CAD-compatible DWG. The open-source candidate remains valuable for research/read-side tooling but does not satisfy the initial production write target.
