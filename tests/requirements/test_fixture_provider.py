from uuid import UUID, uuid4

from ai_vastu.requirements.models import Direction
from ai_vastu.requirements.providers import (
    FixtureRequirementsProvider,
    InterpretationInput,
)

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")


def test_fixture_extracts_explicit_rectangular_prompt() -> None:
    draft = FixtureRequirementsProvider().interpret(
        InterpretationInput(
            draft_id=uuid4(),
            user_id=USER,
            project_id=PROJECT,
            prompt=(
                "30 x 50 ft plot, road on east, true north 0 deg, "
                "3 BHK with kitchen and puja, 2-car parking"
            ),
            references=(),
        )
    )

    assert draft.plot_width_mm is not None
    assert draft.plot_width_mm.value == 9144
    assert draft.plot_depth_mm is not None
    assert draft.plot_depth_mm.value == 15240
    assert draft.road_side is not None
    assert draft.road_side.value == Direction.E
    assert draft.north_rotation_deg is not None
    assert draft.north_rotation_deg.value == 0
    assert draft.bedroom_count is not None
    assert draft.bedroom_count.value == 3
    assert draft.parking_count is not None
    assert draft.parking_count.value == 2
    assert draft.ready_for_confirmation


def test_facing_is_not_silently_treated_as_road() -> None:
    draft = FixtureRequirementsProvider().interpret(
        InterpretationInput(
            draft_id=uuid4(),
            user_id=USER,
            project_id=PROJECT,
            prompt="30 x 50 ft east-facing 2 BHK, true north 0 deg",
            references=(),
        )
    )

    assert draft.entrance_facing is not None
    assert draft.entrance_facing.value == Direction.E
    assert draft.road_side is None
    assert any("road/access" in item for item in draft.questions)
    assert any("not treated as the road side" in item for item in draft.warnings)
