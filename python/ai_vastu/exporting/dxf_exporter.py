from __future__ import annotations

from io import StringIO
from typing import Any

import ezdxf
from ezdxf.enums import InsertUnits, TextEntityAlignment

from .dimension_units import format_dimension_length_mm
from .geometry import (
    north_vector,
    opening_segments,
    polygon_center,
    scene_bounds,
    visible_wall_segments,
)
from .models import DrawingScene, DxfExportConfig, ExportArtifact
from .presentation import build_professional_presentation, site_space_label

# ezdxf 1.4.x does not fully expose its public package API to static typing.
ezdxf_api: Any = ezdxf

_LAYER_SPECS: tuple[tuple[str, int], ...] = (
    ("AIA_PLOT", 8),
    ("AIA_BUILDABLE", 9),
    ("AIA_FLOOR", 7),
    ("AIA_ROAD", 4),
    ("AIA_SITE", 8),
    ("AIA_ROOM", 8),
    ("AIA_WALL_EXT", 7),
    ("AIA_WALL_INT", 8),
    ("AIA_OPENING", 3),
    ("AIA_DOOR", 7),
    ("AIA_WINDOW", 4),
    ("AIA_STAIR", 6),
    ("AIA_STAIR_TREAD", 8),
    ("AIA_FURNITURE", 9),
    ("AIA_FIXTURE", 9),
    ("AIA_DIM", 2),
    ("AIA_DIM_AUTO", 8),
    ("AIA_ANNOT", 7),
    ("AIA_NORTH", 1),
)


def _points(polygon: Any) -> list[tuple[float, float]]:
    return [(float(point.x_mm), float(point.y_mm)) for point in polygon.outer]


def _add_closed_polyline(msp: Any, polygon: Any, layer: str) -> None:
    msp.add_lwpolyline(_points(polygon), close=True, dxfattribs={"layer": layer})


def render_dxf(scene: DrawingScene, config: DxfExportConfig) -> ExportArtifact:
    if scene.scene_hash is None:
        scene = scene.with_scene_hash()

    previous_fixed_metadata = ezdxf_api.options.write_fixed_meta_data_for_testing
    ezdxf_api.options.write_fixed_meta_data_for_testing = True
    try:
        doc = ezdxf_api.new(config.dxf_version, setup=True, units=InsertUnits.Millimeters)
        doc.units = InsertUnits.Millimeters
        doc.header.custom_vars.append("AIA_PLAN_HASH", scene.source_plan_hash)
        assert scene.scene_hash is not None
        doc.header.custom_vars.append("AIA_SCENE_HASH", scene.scene_hash)
        doc.header.custom_vars.append("AIA_REVISION_ID", str(scene.revision_id))
        doc.header.custom_vars.append("AIA_DIMENSION_UNITS", config.dimension_unit.value)
        for name, color in _LAYER_SPECS:
            if name not in doc.layers:
                doc.layers.add(name=name, color=color)
        msp = doc.modelspace()
        presentation = build_professional_presentation(
            scene,
            dimension_unit=config.dimension_unit,
        )

        _add_closed_polyline(msp, scene.plot_boundary, "AIA_PLOT")
        _add_closed_polyline(msp, scene.buildable_boundary, "AIA_BUILDABLE")
        _add_closed_polyline(msp, scene.floor_boundary, "AIA_FLOOR")

        for space in scene.site_spaces:
            _add_closed_polyline(msp, space.polygon, "AIA_SITE")
            msp.add_text(
                site_space_label(space.kind, space.label),
                height=float(config.annotation_height_mm),
                dxfattribs={"layer": "AIA_SITE"},
            ).set_placement(
                polygon_center(space.polygon),
                align=TextEntityAlignment.MIDDLE_CENTER,
            )

        for road in scene.roads:
            for axis in road.axes:
                entity = msp.add_lwpolyline(
                    [(axis.start.x_mm, axis.start.y_mm), (axis.end.x_mm, axis.end.y_mm)],
                    dxfattribs={"layer": "AIA_ROAD"},
                )
                if road.width_mm is not None:
                    entity.dxf.const_width = float(road.width_mm)

        for room in scene.rooms:
            _add_closed_polyline(msp, room.polygon, "AIA_ROOM")
            if config.show_room_labels:
                label = room.name or room.room_type.value.replace("_", " ").title()
                msp.add_text(
                    label,
                    height=float(config.room_label_height_mm),
                    dxfattribs={"layer": "AIA_ANNOT"},
                ).set_placement(
                    polygon_center(room.polygon),
                    align=TextEntityAlignment.MIDDLE_CENTER,
                )

        for segment in visible_wall_segments(scene):
            layer = "AIA_WALL_EXT" if segment.category.value == "EXTERNAL" else "AIA_WALL_INT"
            entity = msp.add_lwpolyline([segment.start, segment.end], dxfattribs={"layer": layer})
            entity.dxf.const_width = float(segment.thickness_mm)

        for opening in opening_segments(scene):
            msp.add_line(opening.start, opening.end, dxfattribs={"layer": "AIA_OPENING"})

        for door in presentation.doors:
            end = door.closed_end if door.sliding else door.open_end
            msp.add_line(door.hinge, end, dxfattribs={"layer": "AIA_DOOR"})
            if door.swing_arc:
                msp.add_lwpolyline(door.swing_arc, dxfattribs={"layer": "AIA_DOOR"})
        for window in presentation.windows:
            for line in window.lines:
                msp.add_line(line.start, line.end, dxfattribs={"layer": "AIA_WINDOW"})

        for stair in presentation.stairs:
            _add_closed_polyline(msp, stair.outline, "AIA_STAIR")
            for tread in stair.treads:
                msp.add_line(tread.start, tread.end, dxfattribs={"layer": "AIA_STAIR_TREAD"})
            msp.add_line(
                stair.arrow.start,
                stair.arrow.end,
                dxfattribs={"layer": "AIA_STAIR"},
            )
        for furniture in scene.furniture:
            _add_closed_polyline(msp, furniture.footprint, "AIA_FURNITURE")
        for fixture in scene.fixtures:
            if fixture.footprint is not None:
                _add_closed_polyline(msp, fixture.footprint, "AIA_FIXTURE")
            elif fixture.anchor is not None:
                msp.add_point(
                    (fixture.anchor.x_mm, fixture.anchor.y_mm),
                    dxfattribs={"layer": "AIA_FIXTURE"},
                )

        if config.show_dimensions:
            for dimension in scene.dimensions:
                length = (
                    (dimension.end.x_mm - dimension.start.x_mm) ** 2
                    + (dimension.end.y_mm - dimension.start.y_mm) ** 2
                ) ** 0.5
                text = dimension.label_override or format_dimension_length_mm(
                    length,
                    config.dimension_unit,
                )
                override = {
                    "dimtxt": float(config.dimension_text_height_mm),
                    "dimasz": float(config.dimension_arrow_size_mm),
                    "dimdec": 0,
                }
                dim = msp.add_aligned_dim(
                    p1=(dimension.start.x_mm, dimension.start.y_mm),
                    p2=(dimension.end.x_mm, dimension.end.y_mm),
                    distance=float(dimension.offset_mm),
                    text=text,
                    dimstyle="EZDXF",
                    override=override,
                    dxfattribs={"layer": "AIA_DIM"},
                )
                dim.render()
            for auto_dimension in presentation.dimensions:
                dx = auto_dimension.dimension_start[0] - auto_dimension.start[0]
                dy = auto_dimension.dimension_start[1] - auto_dimension.start[1]
                distance = (dx * dx + dy * dy) ** 0.5
                dim = msp.add_aligned_dim(
                    p1=auto_dimension.start,
                    p2=auto_dimension.end,
                    distance=float(distance),
                    text=auto_dimension.label,
                    dimstyle="EZDXF",
                    override={
                        "dimtxt": float(config.dimension_text_height_mm),
                        "dimasz": float(config.dimension_arrow_size_mm),
                    },
                    dxfattribs={"layer": "AIA_DIM_AUTO"},
                )
                dim.render()

        if config.show_annotations:
            for annotation in scene.annotations:
                msp.add_text(
                    annotation.text,
                    height=float(config.annotation_height_mm),
                    dxfattribs={"layer": "AIA_ANNOT"},
                ).set_placement(
                    (annotation.anchor.x_mm, annotation.anchor.y_mm),
                    align=TextEntityAlignment.LEFT,
                )

        if config.show_north_arrow:
            bounds = scene_bounds(scene)
            anchor = (
                bounds.max_x_mm - config.north_arrow_length_mm,
                bounds.max_y_mm - config.north_arrow_length_mm,
            )
            vector = north_vector(scene.north_rotation_udeg, float(config.north_arrow_length_mm))
            end = (anchor[0] + vector[0], anchor[1] + vector[1])
            msp.add_line(anchor, end, dxfattribs={"layer": "AIA_NORTH"})
            msp.add_text(
                "N",
                height=float(config.annotation_height_mm),
                dxfattribs={"layer": "AIA_NORTH"},
            ).set_placement(end, align=TextEntityAlignment.MIDDLE_CENTER)

        bounds = scene_bounds(scene)
        msp.dxf.extmin = (bounds.min_x_mm, bounds.min_y_mm, 0.0)
        msp.dxf.extmax = (bounds.max_x_mm, bounds.max_y_mm, 0.0)

        stream = StringIO()
        doc.write(stream)
        content = stream.getvalue().encode(doc.output_encoding)
    finally:
        ezdxf_api.options.write_fixed_meta_data_for_testing = previous_fixed_metadata

    assert scene.scene_hash is not None
    filename = f"floor-{scene.floor_index}-{scene.revision_id}.dxf"
    return ExportArtifact.create(
        format="DXF",
        filename=filename,
        media_type="application/dxf",
        content=content,
        scene_hash=scene.scene_hash,
    )
