from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema import AxisSegment, IntPoint, PlanDocument

from .errors import ExportSceneError
from .models import DrawingScene, SceneRoad


def _plot_edge_axes(document: PlanDocument) -> dict[UUID, AxisSegment]:
    points = document.plot.boundary.outer
    axes: dict[UUID, AxisSegment] = {}
    for index, edge_id in enumerate(document.plot.edge_ids):
        start = points[index]
        end = points[(index + 1) % len(points)]
        axes[edge_id] = AxisSegment(
            start=IntPoint(x_mm=start.x_mm, y_mm=start.y_mm),
            end=IntPoint(x_mm=end.x_mm, y_mm=end.y_mm),
        )
    return axes


def build_drawing_scene(document: PlanDocument, *, floor_id: UUID | None = None) -> DrawingScene:
    if not document.validation.valid:
        raise ExportSceneError("Only a canonically valid PlanDocument may be exported.")
    if not document.floors:
        raise ExportSceneError("PlanDocument has no floor to export.")

    floor = document.floors[0] if floor_id is None else next(
        (item for item in document.floors if item.id == floor_id),
        None,
    )
    if floor is None:
        raise ExportSceneError("Requested export floor is not present in PlanDocument.")

    edge_axes = _plot_edge_axes(document)
    roads: list[SceneRoad] = []
    for road in sorted(document.roads, key=lambda item: str(item.id)):
        try:
            axes = tuple(edge_axes[edge_id] for edge_id in road.plot_edge_ids)
        except KeyError as exc:
            raise ExportSceneError("Road references an unknown plot edge during export.") from exc
        roads.append(
            SceneRoad(
                id=road.id,
                name=road.name,
                axes=axes,
                width_mm=road.width_mm,
                primary_access=road.primary_access,
            )
        )

    floor_boundary = floor.boundary or document.buildable_area.polygon
    scene = DrawingScene(
        project_id=document.project_id,
        revision_id=document.revision_id,
        floor_id=floor.id,
        floor_index=floor.index,
        floor_name=floor.name,
        source_plan_hash=document.compute_content_hash(),
        north_rotation_udeg=document.orientation.north_rotation_udeg,
        plot_boundary=document.plot.boundary,
        buildable_boundary=document.buildable_area.polygon,
        floor_boundary=floor_boundary,
        roads=tuple(roads),
        rooms=tuple(sorted(floor.rooms, key=lambda item: str(item.id))),
        walls=tuple(sorted(floor.walls, key=lambda item: str(item.id))),
        openings=tuple(sorted(floor.openings, key=lambda item: str(item.id))),
        stairs=tuple(sorted(floor.stairs, key=lambda item: str(item.id))),
        fixtures=tuple(sorted(floor.fixtures, key=lambda item: str(item.id))),
        furniture=tuple(sorted(floor.furniture, key=lambda item: str(item.id))),
        dimensions=tuple(sorted(floor.dimensions, key=lambda item: str(item.id))),
        annotations=tuple(sorted(floor.annotations, key=lambda item: str(item.id))),
    )
    return scene.with_scene_hash()
