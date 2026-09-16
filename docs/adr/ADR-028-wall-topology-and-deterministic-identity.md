# ADR-028 — Wall topology and deterministic identity

## Status
Accepted for Phase 8.

## Decision
Build orthogonal wall axes from the union of room-boundary line intervals.

For each horizontal/vertical line:
1. collect every room-boundary interval;
2. split at every interval endpoint;
3. retain atomic intervals covered by at least one room boundary;
4. canonicalize axis direction left-to-right or bottom-to-top;
5. derive wall identity from floor ID plus canonical segment coordinates using UUIDv5.

A segment lying wholly on the canonical buildable boundary is `EXTERNAL`; other room-boundary segments are `INTERNAL`.

## Consequences
- duplicate shared partitions collapse to one wall axis;
- partial overlaps/T-junctions split deterministically;
- rerunning the same geometry build yields identical wall IDs;
- wall axes plus explicit thickness remain the current canonical wall representation.

Wall-face polygons are intentionally deferred. Odd real-world wall thicknesses such as 115 mm must not force silent half-millimetre rounding around a centerline.
