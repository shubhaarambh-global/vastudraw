from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import ezdxf

# ezdxf 1.4.x does not fully expose its public package API to static typing.
ezdxf_api: Any = ezdxf


class DxfImportError(RuntimeError):
    """Raised when a DXF input cannot be parsed safely."""


def _insunits_factor_mm(code: int) -> float | None:
    """Return the AutoCAD INSUNITS conversion factor to millimetres."""

    return {
        0: None,
        1: 25.4,
        2: 304.8,
        4: 1.0,
        5: 10.0,
        6: 1000.0,
    }.get(code)


def _entity_summary(
    entity: Any,
    factor_mm: float | None,
) -> str | None:
    kind = str(entity.dxftype())
    layer = str(entity.dxf.layer) if hasattr(entity.dxf, "layer") else "0"

    factor = factor_mm or 1.0

    try:
        if kind == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end

            return (
                f"LINE layer={layer} "
                f"start=({start.x * factor:.3f},"
                f"{start.y * factor:.3f})mm "
                f"end=({end.x * factor:.3f},"
                f"{end.y * factor:.3f})mm"
            )

        if kind == "LWPOLYLINE":
            points = list(entity.get_points("xy"))[:32]

            encoded = ";".join(
                f"{float(x) * factor:.3f},{float(y) * factor:.3f}" for x, y in points
            )

            return f"LWPOLYLINE layer={layer} points_mm={encoded}"

        if kind in {"TEXT", "MTEXT"}:
            value = str(entity.dxf.text) if kind == "TEXT" else str(entity.plain_text())

            return f"{kind} layer={layer} text={value[:300]!r}"

        if kind == "DIMENSION":
            text = str(getattr(entity.dxf, "text", ""))

            measurement = entity.get_measurement()

            return (
                f"DIMENSION layer={layer} "
                f"text={text[:120]!r} "
                f"measurement_mm="
                f"{float(measurement) * factor:.3f}"
            )

        if kind == "INSERT":
            name = str(entity.dxf.name)
            point = entity.dxf.insert

            return (
                f"INSERT layer={layer} "
                f"block={name!r} "
                f"at=({point.x * factor:.3f},"
                f"{point.y * factor:.3f})mm"
            )

    except (AttributeError, TypeError, ValueError):
        return f"{kind} layer={layer}"

    return None


def summarize_dxf_bytes(
    dxf_bytes: bytes,
) -> str:
    """Extract deterministic semantic evidence from a DXF file.

    DXF coordinates are only considered authoritative when drawing units
    can be resolved from INSUNITS.
    """

    with tempfile.TemporaryDirectory(prefix="ai-vastu-dxf-") as temp_dir:
        path = Path(temp_dir) / "input.dxf"
        path.write_bytes(dxf_bytes)

        try:
            doc = ezdxf_api.readfile(path)
        except Exception as exc:
            raise DxfImportError(f"Could not parse DXF input: {exc}") from exc

        code = int(doc.header.get("$INSUNITS", 0) or 0)

        factor = _insunits_factor_mm(code)
        modelspace = doc.modelspace()

        lines = [
            "CAD EXTRACTION SUMMARY",
            f"DXF version={doc.dxfversion}",
            f"INSUNITS={code}",
            (f"unit_factor_mm={factor if factor is not None else 'UNKNOWN'}"),
            ("Coordinates below are authoritative CAD coordinates only when units are known."),
        ]

        count = 0

        for entity in modelspace:
            summary = _entity_summary(
                entity,
                factor,
            )

            if summary is None:
                continue

            lines.append(summary)
            count += 1

            if count >= 500:
                lines.append("TRUNCATED_AFTER=500_ENTITIES")
                break

        return "\n".join(lines)
