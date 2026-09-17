from pathlib import Path
from uuid import UUID

from ai_vastu.plan_intake import (
    PlanAnalysisStore,
    PlanGeometryConfirmationInput,
)

PROJECT_ID = UUID("30000000-0000-0000-0000-000000000265")
INTAKE_ID = UUID("40000000-0000-0000-0000-000000000265")


def test_user_confirmation_freezes_exact_rectangular_envelope(
    tmp_path: Path,
) -> None:
    intake_dir = tmp_path / str(PROJECT_ID) / str(INTAKE_ID)
    intake_dir.mkdir(parents=True)

    store = PlanAnalysisStore(tmp_path)
    record = store.save_confirmation(
        PROJECT_ID,
        INTAKE_ID,
        PlanGeometryConfirmationInput(
            width_mm=9144,
            depth_mm=15240,
            north_rotation_deg=0.0,
            road_side="E",
            preserve_outer_envelope=True,
        ),
    )

    assert record.confirmed_by_user is True
    assert record.exact_area_mm2 == 9144 * 15240
    assert record.preserve_outer_envelope is True
    assert store.get_confirmation(PROJECT_ID, INTAKE_ID) == record
