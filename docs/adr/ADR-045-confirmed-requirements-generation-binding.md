# ADR-045 — Bind confirmed requirements to the existing deterministic generator

## Status

Accepted for Phase 24B.

## Context

The Phase 24 generation contract inspection proved that the production generator
accepts `ArchitecturalGenerationRequest` and returns
`ArchitecturalGenerationResult`.

The request requires exact room minima and runtime settings that are not produced
by the multimodal model.

## Decision

The adapter:
- imports and validates the existing generation model directly;
- uses deterministic, versioned product defaults for room minima and runtime
  settings;
- requires an explicit `accept_profile_defaults=true` acknowledgement;
- records those values as documented assumptions;
- never asks the multimodal model to invent required minimum dimensions;
- never duplicates the CP-SAT/geometry/validation pipeline.

Billing authorization occurs before generation. The free successful generation is
consumed only when the deterministic pipeline returns `ACCEPTED`.

The current generation contract contains no true-North/road input and no frozen
Vastu result, so Phase 24B must expose that limitation rather than falsely
claim Vastu-aware generation. Final Phase 24 integration must use the exact
Vastu/scoring/project contracts exported by the inspection gate.
