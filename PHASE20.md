# Phase 20 — Vastu Specification v1.0 production-review track

## Objective

Move the empty Vastu authoring shell into a source-backed review state without fabricating the human domain approval required by the production contract.

## Phase 20A — included in this overlay

- registers traceable public source records;
- adds four conservative residential room-placement candidates;
- normalizes every rule into the typed Vastu rule model;
- keeps every rule `SOFT` so Vastu never overrides code/safety constraints;
- uses an eight-direction `zone_direction_8` candidate metric with `CENTROID_IN_ZONE` semantics;
- marks source validation complete but geometry semantics pending review;
- generates deterministic human review packets;
- keeps the manifest `IN_REVIEW` and production rule count at zero;
- keeps all three Vastu MVP blockers active.

## Phase 20B — intentionally not fabricated

To freeze v1.0, every production rule must obtain an actual human `VASTU_EXPERT` approval and geometry-semantics review. Only then may the release compiler:

1. promote rules to `FROZEN`;
2. mark reviews `APPROVED`;
3. compile the production rule bundle;
4. pin the exact SHA-256 bundle hash in `manifest.json`;
5. move the specification lifecycle to `FROZEN`;
6. clear the final three MVP blockers.

The model must not create an expert attestation on behalf of a person who has not reviewed the packet.
