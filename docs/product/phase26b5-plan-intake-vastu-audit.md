# Phase 26B.5 — Existing Plan Intake + Vastu Audit

Phase 26B.5 adds a second product entry path for users who already have a plan.

## Supported intake

- JPG / JPEG
- PNG
- PDF
- DXF
- DWG (stored natively; analysis uses a configured DWG-to-DXF adapter)

## Authority boundary

AI recognition is evidence, not authoritative CAD geometry.

The recognizer may identify room labels, approximate room centroids, printed
dimensions, North, road side and other plan semantics. Pixel measurements are
never silently promoted to exact millimetres. Exact alternate-plan generation
remains locked until the user confirms the outer envelope and true North.

## Vastu audit

The recognized plan is evaluated against the Phase 26B soft Vastu catalog.
The score is explicitly provisional. If true North or room positions are
missing, the application returns no score rather than fabricating one.

Traditional Vastu guidance remains soft planning guidance. It is not a
building-safety or regulatory compliance check.

## CAD handling

DXF is parsed with ezdxf into a bounded semantic/vector summary.

DWG is never renamed to DXF. Production DWG intake requires:

- `AI_VASTU_DWG_IMPORT_EXECUTABLE`
- `AI_VASTU_DWG_IMPORT_ARGS_JSON`

The argv JSON must contain `{input_dwg}` and `{output_dxf}` placeholders and
executes with `shell=False`.

## Phase 26C handoff

Phase 26C consumes either:

1. confirmed prompt-only requirements, or
2. an uploaded-plan analysis plus a user-confirmed exact envelope.

Both paths then enter deterministic multi-candidate generation, hard
architectural validation, separate architecture/Vastu scoring and weighted
ranking.
