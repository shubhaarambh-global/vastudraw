# Constraint compiler contract — Phase 6

The compiler accepts a verified `BuildableArea`, available floor indices, normalized `RoomRequirement` records, and explicit assumptions.

It performs only deterministic compilation and exact preflight checks. It does **not** solve placement, create walls, evaluate real Vastu rules, or add hidden defaults.

## Hard output

- containment within the buildable area;
- minimum/maximum width and depth;
- minimum/maximum area;
- aspect-ratio bounds;
- available-floor domain;
- hard adjacency prohibitions.

## Soft output

- preferred width/depth/area;
- floor preferences;
- adjacency preferences;
- soft adjacency avoidance;
- privacy/daylight/ventilation/user priority metadata.

## Fail-closed preflight

Compilation rejects unavailable floor preferences, contradictory adjacency requirements, impossible dimension/area combinations, absent required adjacency targets, and total minimum room area that exceeds total buildable floor capacity.

The compiler preserves explicit assumptions exactly and never manufactures new assumptions.
