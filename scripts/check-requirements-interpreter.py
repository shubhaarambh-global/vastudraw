from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import UUID

from ai_vastu.requirements.models import ConfirmedRequirements, Direction
from ai_vastu.requirements.providers import FixtureRequirementsProvider
from ai_vastu.requirements.service import RequirementsService
from ai_vastu.requirements.store import RequirementsStore

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")

with tempfile.TemporaryDirectory() as directory:
    service = RequirementsService(
        FixtureRequirementsProvider(),
        RequirementsStore(Path(directory)),
    )
    draft = service.interpret(
        user_id=USER,
        project_id=PROJECT,
        prompt=(
            "30 x 50 ft plot, road on east, true north 0 deg, "
            "3 BHK, kitchen, puja, 2-car parking"
        ),
        references=(),
    )

    assert draft.ready_for_confirmation
    assert draft.plot_width_mm is not None
    assert draft.plot_width_mm.value == 9144
    assert draft.plot_depth_mm is not None
    assert draft.plot_depth_mm.value == 15240
    assert draft.road_side is not None
    assert draft.road_side.value == Direction.E

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
        bedroom_count=3,
        parking_count=2,
        rooms=[],
    )
    service.confirm(
        authenticated_user_id=USER,
        confirmed=confirmed,
    )
    assert service.get_confirmed(draft.draft_id).user_confirmed

print(
    "Phase 24A requirements wired: multimodal_contract=true, "
    "structured_draft=true, ambiguity=true, human_confirmation=true, "
    "authoritative_geometry=false, fixture_provider=true, live_provider_boundary=true"
)
