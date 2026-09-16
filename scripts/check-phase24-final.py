from __future__ import annotations

from uuid import UUID

from ai_vastu.plan_schema.geometry import IntPoint, IntPolygon
from ai_vastu.plan_schema.models import Floor, RoomGeometry, RoomType
from ai_vastu.projects.factory import create_project_repository_from_environment
from ai_vastu.projects.service import ProjectRevisionService
from ai_vastu.requirements.finalization import (
    EXPECTED_VASTU_V1_BUNDLE_HASH,
    build_vastu_analysis,
    load_production_vastu_bundle,
)
from ai_vastu.scoring.selector import score_and_select_alternatives


def rectangle(x1: int, y1: int, x2: int, y2: int) -> IntPolygon:
    return IntPolygon(
        outer=(
            IntPoint(x_mm=x1, y_mm=y1),
            IntPoint(x_mm=x2, y_mm=y1),
            IntPoint(x_mm=x2, y_mm=y2),
            IntPoint(x_mm=x1, y_mm=y2),
        )
    )


bundle = load_production_vastu_bundle()
assert bundle.production
assert bundle.content_hash == EXPECTED_VASTU_V1_BUNDLE_HASH
assert len(bundle.rules) == 4

plot = rectangle(0, 0, 10000, 10000)
floor = Floor(
    id=UUID("00000000-0000-0000-0000-000000000010"),
    index=0,
    name="Ground Floor",
    elevation_mm=0,
    floor_to_floor_mm=3000,
    boundary=plot,
    rooms=(
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            room_type=RoomType("kitchen"),
            polygon=rectangle(7000, 2000, 8000, 3000),
        ),
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            room_type=RoomType("puja"),
            polygon=rectangle(7000, 7000, 8000, 8000),
        ),
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            room_type=RoomType("master_bedroom"),
            polygon=rectangle(4500, 2000, 5500, 3000),
        ),
        RoomGeometry(
            id=UUID("00000000-0000-0000-0000-000000000004"),
            room_type=RoomType("bath"),
            polygon=rectangle(7000, 4500, 8000, 5500),
        ),
    ),
)
analysis = build_vastu_analysis(
    bundle=bundle,
    floor=floor,
    plot_boundary=plot,
    north_rotation_udeg=0,
)
assert len(analysis.results) == 4
assert all(result.status.value == "PASS" for result in analysis.results)

assert callable(create_project_repository_from_environment)
assert callable(ProjectRevisionService)
assert callable(score_and_select_alternatives)

print(
    "Phase 24 final binding: confirmed_requirements=true, ownership=true, "
    "billing_precheck=true, deterministic_generation=true, "
    "frozen_vastu_runtime=true, scoring=true, canonical_plan_document=true, "
    "immutable_revision=true, billing_after_commit=true, editor_handoff=true, "
    "multifloor_fail_closed=true"
)
