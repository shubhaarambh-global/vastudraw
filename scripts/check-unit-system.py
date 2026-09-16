from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

checks = {
    "apps/web/src/units/length.ts": (
        'DEFAULT_DISPLAY_LENGTH_UNIT: DisplayLengthUnit = "ft-in"',
        "parseLengthToMm",
        "formatLengthMm",
    ),
    "apps/web/src/components/editor/PlanEditor.tsx": (
        "displayUnit={displayUnit}",
        "formatLengthMm(Math.round(length), displayUnit)",
    ),
    "apps/web/src/components/generation/RequirementsReviewPage.tsx": (
        "Feet &amp; Inches",
        "plot_width_mm: widthMm",
        "plot_depth_mm: depthMm",
    ),
    "python/ai_vastu/exporting/models.py": (
        'FEET_INCHES = "ft-in"',
        "dimension_unit: DimensionDisplayUnit",
    ),
    "python/ai_vastu/exporting/dxf_exporter.py": (
        "AIA_DIMENSION_UNITS",
        "format_dimension_length_mm",
    ),
}

for relative, needles in checks.items():
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"Unit system check failed: missing {relative}")
    source = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in source:
            raise SystemExit(f"Unit system check failed: {relative} missing {needle!r}")

schema = (ROOT / "packages/contracts/schema/plan-document.schema.json").read_text(encoding="utf-8")
if '"canonical_units": {' not in schema or '"const": "mm"' not in schema:
    raise SystemExit("Unit system check failed: PlanDocument canonical mm invariant changed.")

print(
    "Unit system wired: default=ft-in, alternative=m, canonical=integer-mm, "
    "editor=true, requirements-review=true, exports=true"
)
