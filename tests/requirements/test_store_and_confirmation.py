from pathlib import Path
from uuid import UUID

import pytest

from ai_vastu.requirements.models import (
    ConfirmedRequirements,
    Direction,
)
from ai_vastu.requirements.providers import FixtureRequirementsProvider
from ai_vastu.requirements.service import RequirementsService
from ai_vastu.requirements.store import RequirementsStore

USER = UUID("11111111-1111-1111-1111-111111111111")
OTHER = UUID("99999999-9999-9999-9999-999999999999")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")


def _service(tmp_path: Path) -> RequirementsService:
    return RequirementsService(
        FixtureRequirementsProvider(),
        RequirementsStore(tmp_path),
    )


def test_confirmation_is_separate_from_interpretation(tmp_path: Path) -> None:
    service = _service(tmp_path)
    draft = service.interpret(
        user_id=USER,
        project_id=PROJECT,
        prompt="30 x 50 ft, road on east, true north 0 deg, 2 BHK",
        references=(),
    )

    confirmed = ConfirmedRequirements(
        draft_id=draft.draft_id,
        user_id=USER,
        project_id=PROJECT,
        user_confirmed=True,
        plot_width_mm=9144,
        plot_depth_mm=15240,
        north_rotation_deg=0,
        road_side=Direction.E,
        floor_count=1,
        bedroom_count=2,
        parking_count=1,
        rooms=[],
    )

    result = service.confirm(
        authenticated_user_id=USER,
        confirmed=confirmed,
    )

    assert result.user_confirmed is True
    assert service.get_confirmed(draft.draft_id) == confirmed


def test_other_user_cannot_confirm_draft(tmp_path: Path) -> None:
    service = _service(tmp_path)
    draft = service.interpret(
        user_id=USER,
        project_id=PROJECT,
        prompt="30 x 50 ft, road on east, true north 0 deg",
        references=(),
    )

    confirmed = ConfirmedRequirements(
        draft_id=draft.draft_id,
        user_id=OTHER,
        project_id=PROJECT,
        user_confirmed=True,
        plot_width_mm=9144,
        plot_depth_mm=15240,
        north_rotation_deg=0,
        road_side=Direction.E,
        floor_count=1,
        bedroom_count=0,
        rooms=[],
    )

    with pytest.raises(PermissionError):
        service.confirm(
            authenticated_user_id=OTHER,
            confirmed=confirmed,
        )
