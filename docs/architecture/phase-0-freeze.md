# Phase 0 Architecture Freeze

Status: **ACCEPTED FOR IMPLEMENTATION BOOTSTRAP**

## Frozen boundaries

1. Canonical linear geometry uses signed integer millimetres.
2. Canonical angular orientation will use fixed-point integer angular units; Phase 1 freezes the exact field representation.
3. Authoritative geometry is owned by the deterministic domain core, never by the LLM or browser renderer.
4. `PlanDocument` is the single canonical plan state used by editor, validation, scoring, and exporters.
5. Floor-owned entities must not be duplicated as conflicting root-level authoritative geometry.
6. Vastu and building regulation engines are independent modules.
7. Hard validation failures fail closed.
8. Accepted plan revisions are immutable and reproducible.
9. OR-Tools CP-SAT is the primary V1 planning solver.
10. Clipper2 is the intended primary polygon kernel behind an internal adapter; Shapely/GEOS is an independent verification layer.
11. Konva may render/edit views but never owns authoritative dimensions.
12. DXF uses a pluggable exporter, initially ezdxf.
13. DWG is a pluggable, separately qualified capability; no production claim before round-trip compatibility testing.
14. Phase 0 contains no production Vastu knowledge, solver model, or CAD geometry logic.

## Phase 1 entry condition

Phase 0 quality gate must pass in the developer's WSL environment before canonical schema implementation starts.
