# Phase 13 export contract

## Authority

`PlanDocument` remains authoritative geometry. `DrawingScene` is a deterministic export projection and carries both source-plan and scene SHA-256 hashes.

## Coordinate units

Scene geometry remains millimetres with drawing `+Y` upward.

- DXF modelspace: 1 drawing unit = 1 mm.
- PDF: millimetres are scaled to PDF points only at rendering time.
- JPG: millimetres are scaled to pixels only at rendering time and pixels are never authoritative.

## Wall/opening semantics

Walls are represented canonically by axis plus thickness. Export derivation splits a wall axis around canonical opening intervals. This preserves opening widths while avoiding half-millimetre wall-face canonicalization for odd wall thicknesses such as 115 mm.

## DXF layers

Phase 13 emits stable layers including:

`AIA_PLOT`, `AIA_BUILDABLE`, `AIA_FLOOR`, `AIA_ROAD`, `AIA_ROOM`, `AIA_WALL_EXT`, `AIA_WALL_INT`, `AIA_OPENING`, `AIA_STAIR`, `AIA_FURNITURE`, `AIA_FIXTURE`, `AIA_DIM`, `AIA_ANNOT`, `AIA_NORTH`.

## Determinism

- Scene ordering is UUID-stable.
- ReportLab uses invariant mode.
- ezdxf fixed metadata mode is enabled only while writing the artifact and restored afterward.
- Export artifact hashes are content hashes, not geometry authority.
