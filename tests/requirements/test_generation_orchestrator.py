from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

from ai_vastu.billing import BillingService
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository
from ai_vastu.requirements.generation_orchestrator import (
    ConfirmedGenerationOrchestrator,
)
from ai_vastu.requirements.models import (
    ConfirmedRequirements,
    ConfirmedRoomRequirement,
    Direction,
)
from ai_vastu.requirements.store import RequirementsStore

USER = UUID("11111111-1111-1111-1111-111111111111")
PROJECT = UUID("22222222-2222-2222-2222-222222222222")


def test_orchestrator_registers_entitlement_and_does_not_consume_free_on_rejection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    store = RequirementsStore(tmp_path / "requirements")
    draft_id = uuid4()

    # Seed the draft file because confirmation persistence requires it.
    from ai_vastu.requirements.models import RequirementDraft

    draft = RequirementDraft(
        draft_id=draft_id,
        user_id=USER,
        project_id=PROJECT,
        prompt="30 x 50 ft, road on east, north 0 deg, one bedroom",
        provider="fixture",
    )
    store.save_draft(draft)

    confirmed = ConfirmedRequirements(
        draft_id=draft_id,
        user_id=USER,
        project_id=PROJECT,
        user_confirmed=True,
        plot_width_mm=9144,
        plot_depth_mm=15240,
        north_rotation_deg=0,
        road_side=Direction.E,
        floor_count=1,
        bedroom_count=1,
        parking_count=0,
        rooms=[
            ConfirmedRoomRequirement(room_type="bedroom", quantity=1),
        ],
    )
    store.save_confirmed(confirmed)

    billing_repository = SqliteBillingRepository(tmp_path / "billing.sqlite3")
    billing = BillingService(billing_repository)

    from ai_vastu.generation.models import ArchitecturalGenerationResult

    fake_result = cast(
        ArchitecturalGenerationResult,
        SimpleNamespace(
            disposition=SimpleNamespace(value="UNSOLVED"),
        ),
    )

    monkeypatch.setattr(
        "ai_vastu.requirements.generation_orchestrator.run_compiled_generation",
        lambda _compiled: fake_result,
    )

    orchestrator = ConfirmedGenerationOrchestrator(
        requirements_store=store,
        billing_service=billing,
    )
    run = orchestrator.run(
        authenticated_user_id=USER,
        project_id=PROJECT,
        draft_id=draft_id,
    )

    assert run.result.disposition.value == "UNSOLVED"
    assert not run.free_generation_consumed
    assert billing.snapshot(str(USER)).free_generation_available
    billing_repository.close()
