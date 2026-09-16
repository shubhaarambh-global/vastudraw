from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_vastu.plan_schema import (
    Floor,
    Opening,
    OpeningKind,
    PlanDocument,
    Plot,
    PlotGeometryType,
    PlotInputSource,
    VerificationStatus,
)

from .sample import EDGE_IDS, PLOT_ID, rectangle, sample_plan


def test_plot_requires_one_edge_id_per_outer_edge() -> None:
    with pytest.raises(ValidationError, match="one ID per outer boundary edge"):
        Plot(
            id=PLOT_ID,
            geometry_type=PlotGeometryType.RECTANGLE,
            boundary=rectangle(),
            edge_ids=EDGE_IDS[:3],
            input_source=PlotInputSource.MANUAL,
            verification_status=VerificationStatus.USER_VERIFIED,
        )


def test_opening_cannot_reference_unknown_wall() -> None:
    plan = sample_plan()
    floor = Floor(
        id=plan.floors[0].id,
        index=0,
        name="Ground Floor",
        elevation_mm=0,
        floor_to_floor_mm=3_300,
        boundary=rectangle(),
        openings=(
            Opening(
                id=UUID("55555555-5555-5555-5555-555555555555"),
                wall_id=UUID("66666666-6666-6666-6666-666666666666"),
                kind=OpeningKind.DOOR,
                offset_from_wall_start_mm=0,
                width_mm=900,
                height_mm=2_100,
            ),
        ),
    )
    payload = plan.model_dump()
    payload["floors"] = (floor,)
    payload["content_hash"] = None
    with pytest.raises(ValidationError, match="unknown wall ID"):
        PlanDocument.model_validate(payload)
