# Phase 12 interactive editor contract

## Authority

`PlanDocument` integer millimetres remain authoritative. Konva stage coordinates are presentation/input coordinates only. The editor never writes pixel values into the canonical document.

## Coordinate transform

Canonical drawing axes follow ADR-016: `+X` right and `+Y` up. Canvas `+Y` is down, therefore the renderer explicitly inverts Y at the view transform.

## Editing model

Phase 12 stages exact integer-mm commands against a base `revision_id`. It does not mutate the loaded `PlanDocument`. Room dimension requests are intent for a future backend re-solve. Wall/opening previews are visibly marked pending until a validated backend revision replaces the base document.

Supported staged commands:

- room lock/unlock;
- wall lock/unlock;
- orthogonal wall parallel move by exact mm delta;
- room target width/depth request;
- opening offset move;
- opening width resize.

Undo/redo operates only on staged commands.

## View features

- pan and cursor-anchored zoom;
- fit to floor;
- grid and rulers;
- room, wall, opening and dimension selection;
- visibility layers;
- exact numeric inspector;
- staged edit count and change-set submission boundary.

## Safety constraints

- edit quantities must be JavaScript-safe integer millimetres;
- fractional mm commands are rejected;
- canonical coordinates outside JavaScript safe-integer range must not be edited in-browser;
- editor previews are not validation results;
- backend solve/geometry/validation remains required before a new revision is authoritative.
