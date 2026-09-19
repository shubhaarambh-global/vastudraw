---
name: vastudraw-plan-quality
description: >-
  Use when reviewing or improving generated residential plans, architectural
  topology, circulation, site use, room relationships, dimensional quality,
  parking, stairs, wet areas, candidate diversity, or the professional 2D plan
  renderer. Evaluates architectural usability rather than trusting scores alone.
---

# Vastudraw Architectural Plan Quality Review

Use this skill whenever the task asks whether a generated plan is actually
architecturally usable, or when changing logic that materially affects plan
quality.

Scores alone are not proof of architectural quality.

## Review order

Evaluate in this order:

1. program completeness;
2. physical accessibility;
3. topology and room relationships;
4. room dimensional usability;
5. site utilization;
6. parking usability;
7. sanitary/service logic;
8. puja separation;
9. daylight/ventilation opportunities where represented;
10. multi-floor/vertical circulation;
11. candidate diversity;
12. drawing/presentation quality.

A severe failure near the top cannot be compensated by a high aggregate score.

## Program completeness

Check:

- requested bedrooms;
- requested sanitary spaces;
- kitchen;
- living/dining interpretation;
- puja;
- parking;
- custom rooms;
- floor count;
- floor assignment.

No requested space may disappear.

No unintended duplicate should be introduced.

## Circulation

Ask whether a person can actually traverse the plan.

Check:

- primary entry;
- living/public access;
- kitchen access;
- bedroom access;
- sanitary access;
- lobby/passage function;
- stair access for multi-floor buildings;
- door-capable shared walls.

Reject fake connectivity through:
- corner touches;
- microscopic shared edges;
- toilets as transit;
- unrelated bedrooms as required public circulation.

## Room relationships

Evaluate semantically rather than only geometrically.

Examples:

- kitchen should relate coherently to dining/living according to brief;
- bedrooms should have reasonable privacy;
- toilets should not dominate public views when avoidable;
- puja should not violate sanitary separation;
- parking should connect meaningfully to entrance/site access;
- parents/guest bedroom preferences should be respected when confirmed.

Do not invent requirements absent from the brief or project rules.

## Dimensional sanity

Check room proportions and dimensions, not only area.

Flag:

- extremely narrow rooms;
- unusable aspect ratios;
- oversized sanitary/parking/service spaces used as area fillers;
- implausibly small door-capable wall segments;
- circulation widths that cannot function.

Use repository constraints as authority.

Do not invent building-code compliance claims that the repository does not
encode.

## Site utilization

Distinguish:

- plot;
- buildable envelope;
- occupied rooms;
- purposeful site space;
- open-to-sky space;
- residual unexplained geometry.

"Use the full site" does not mean "construct on 100% of the land."

Open space, landscape, vehicle access, lightwells, yards, porches, setbacks,
and courtyards may be valid when explicitly justified.

Large unexplained voids inside confirmed buildable geometry are not acceptable.

## Multi-floor quality

For multi-floor plans check:

- coherent program distribution;
- complete building circulation;
- continuous vertical core;
- stair access on each served floor;
- upper-floor footprint logic;
- wet-area coordination;
- no independent unrelated floor plans masquerading as one building.

## Candidate diversity

Candidate alternatives should differ meaningfully in:

- zoning;
- topology;
- circulation;
- room placement;
- vertical-core position where appropriate.

Do not count:
- UUID changes;
- title/rationale changes;
- score-only changes;
- tiny solver jitter

as architectural diversity.

## Renderer quality

When working on 2D architectural presentation, ensure canonical geometry is
translated into recognizable architectural drawings.

Expected professional plan language may include, where canonical data exists:

- proper wall thickness/line hierarchy;
- door leaves and swings;
- windows/openings;
- stairs;
- sanitary fixtures;
- kitchen fixtures;
- furniture where appropriate;
- room labels;
- dimensions;
- north arrow;
- scale;
- external/site dimensions;
- parking/vehicle representation;
- clear sheet hierarchy.

The renderer must not invent geometry that contradicts the canonical
PlanDocument.

Presentation improvements must not hide invalid architecture.
