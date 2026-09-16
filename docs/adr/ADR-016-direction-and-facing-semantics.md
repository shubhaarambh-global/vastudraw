# ADR-016 — Direction and Facing Semantics

## Status
Accepted for Phase 2.

## Coordinate convention

- Drawing `+X` points right.
- Drawing `+Y` points up.
- Drawing bearing `0°` is drawing `+Y`.
- Bearings increase clockwise.
- `Orientation.north_rotation_udeg` is the clockwise drawing bearing at which true North lies.
- True bearing of a drawing vector is therefore:

  `drawing_bearing - north_rotation (mod 360°)`.

## Plot-edge facing

A boundary edge's **facing direction is its outward normal**, not its tangent direction.

For a counter-clockwise plot ring, the interior lies left of each traversed edge, so the outward normal is the right normal (`tangent + 90°`). For a clockwise ring it is the left normal (`tangent - 90°`).

## Roads

Road/access assignment and true North are independent facts. A road never establishes North. A compound road spanning multiple edges may have no single facing direction; the engine must return an ambiguous result rather than invent one.

## Direction labels

The simple eight-way labels `N/NE/E/SE/S/SW/W/NW` are derived classifications of exact microdegree bearings. They are not authoritative angular storage.
