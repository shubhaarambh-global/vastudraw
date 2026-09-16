# ADR-038 — JPG, vector PDF and DXF backends

Status: Accepted for Phase 13

## Context

The product requires portable raster previews, printable vector drawings and CAD exchange while preserving the same millimetre geometry.

## Decision

Phase 13 uses:

- Pillow for deterministic JPG rasterization;
- ReportLab `pdfgen` for vector PDF generation with invariant output mode;
- ezdxf for DXF R2018 modelspace output in millimetres.

DXF walls are emitted as constant-width lightweight polylines after canonical openings are subtracted from wall axes. Canonical dimensions are emitted as native DXF DIMENSION entities. PDF remains vector geometry; JPG is a presentation raster only.

Vendor libraries are confined to dedicated exporter adapters. DrawingScene construction and geometry derivation remain vendor-independent.

DWG is explicitly not implemented in Phase 13 and remains subject to Phase 14 backend qualification.
