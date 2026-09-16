from __future__ import annotations

from uuid import UUID

from project_smoke_fixture import REVISION_2, sample_plan

from ai_vastu.plan_schema import (
    Annotation,
    AxisSegment,
    Dimension,
    IntPoint,
    Opening,
    OpeningKind,
    RoomGeometry,
    RoomType,
    Wall,
    WallCategory,
)

ROOM_A = UUID("55555555-5555-5555-5555-555555555551")
ROOM_B = UUID("55555555-5555-5555-5555-555555555552")
WALL_IDS = tuple(UUID(f"66666666-6666-6666-6666-66666666666{i}") for i in range(1, 6))
OPENING_ID = UUID("77777777-7777-7777-7777-777777777777")
DIM_ID = UUID("88888888-8888-8888-8888-888888888888")
ANNOTATION_ID = UUID("99999999-9999-9999-9999-999999999999")


def export_smoke_plan():
    document = sample_plan(REVISION_2)
    boundary = document.floors[0].boundary
    assert boundary is not None
    x0 = 0
    x1 = 4_572
    x2 = 9_144
    y0 = 0
    y1 = 15_240
    room_a = RoomGeometry(
        id=ROOM_A,
        room_type=RoomType.LIVING,
        name="Living",
        polygon=boundary.model_copy(
            update={
                "outer": (
                    IntPoint(x_mm=x0, y_mm=y0),
                    IntPoint(x_mm=x1, y_mm=y0),
                    IntPoint(x_mm=x1, y_mm=y1),
                    IntPoint(x_mm=x0, y_mm=y1),
                )
            }
        ),
    )
    room_b = RoomGeometry(
        id=ROOM_B,
        room_type=RoomType.KITCHEN,
        name="Kitchen",
        polygon=boundary.model_copy(
            update={
                "outer": (
                    IntPoint(x_mm=x1, y_mm=y0),
                    IntPoint(x_mm=x2, y_mm=y0),
                    IntPoint(x_mm=x2, y_mm=y1),
                    IntPoint(x_mm=x1, y_mm=y1),
                )
            }
        ),
    )
    walls = (
        Wall(
            id=WALL_IDS[0],
            axis=AxisSegment(
                start=IntPoint(x_mm=x0, y_mm=y0),
                end=IntPoint(x_mm=x2, y_mm=y0),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[1],
            axis=AxisSegment(
                start=IntPoint(x_mm=x2, y_mm=y0),
                end=IntPoint(x_mm=x2, y_mm=y1),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[2],
            axis=AxisSegment(
                start=IntPoint(x_mm=x2, y_mm=y1),
                end=IntPoint(x_mm=x0, y_mm=y1),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[3],
            axis=AxisSegment(
                start=IntPoint(x_mm=x0, y_mm=y1),
                end=IntPoint(x_mm=x0, y_mm=y0),
            ),
            thickness_mm=230,
            height_mm=3_000,
            category=WallCategory.EXTERNAL,
        ),
        Wall(
            id=WALL_IDS[4],
            axis=AxisSegment(
                start=IntPoint(x_mm=x1, y_mm=y0),
                end=IntPoint(x_mm=x1, y_mm=y1),
            ),
            thickness_mm=115,
            height_mm=3_000,
            category=WallCategory.INTERNAL,
        ),
    )
    floor = document.floors[0].model_copy(
        update={
            "rooms": (room_a, room_b),
            "walls": walls,
            "openings": (
                Opening(
                    id=OPENING_ID,
                    wall_id=WALL_IDS[4],
                    kind=OpeningKind.DOOR,
                    offset_from_wall_start_mm=2_000,
                    width_mm=900,
                    height_mm=2_100,
                ),
            ),
            "dimensions": (
                Dimension(
                    id=DIM_ID,
                    start=IntPoint(x_mm=x0, y_mm=y0),
                    end=IntPoint(x_mm=x2, y_mm=y0),
                    offset_mm=600,
                ),
            ),
            "annotations": (
                Annotation(
                    id=ANNOTATION_ID,
                    anchor=IntPoint(x_mm=300, y_mm=14_600),
                    text="GROUND FLOOR",
                    category="title",
                ),
            ),
        }
    )
    return document.model_copy(
        update={"floors": (floor,), "content_hash": None}
    ).with_content_hash()
