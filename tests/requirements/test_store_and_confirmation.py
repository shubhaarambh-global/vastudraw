import os
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


def test_draft_and_reconfirmation_replace_json_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = _service(tmp_path)
    draft = service.interpret(
        user_id=USER,
        project_id=PROJECT,
        prompt="30 x 50 ft, road on east, 2 BHK",
        references=(),
    )
    store = RequirementsStore(tmp_path)
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
    store.save_confirmed(confirmed)
    original_replace = os.replace
    source_paths: list[Path] = []

    def checked_replace(source: str | Path, destination: str | Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        assert source_path.parent == destination_path.parent == tmp_path
        assert source_path != destination_path
        assert source_path.is_file()
        source_paths.append(source_path)
        original_replace(source_path, destination_path)

    monkeypatch.setattr("ai_vastu.requirements.store.os.replace", checked_replace)
    updated_draft = draft.model_copy(update={"prompt": "Updated prompt"})
    store.save_draft(updated_draft)
    revised = confirmed.model_copy(update={"parking_count": 2})
    store.save_confirmed(revised)
    assert store.get_draft(draft.draft_id) == updated_draft
    assert store.get_confirmed(draft.draft_id) == revised
    assert len(set(source_paths)) == 2
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("record_kind", ["draft", "confirmed"])
def test_failed_replace_preserves_readable_prior_json_and_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record_kind: str
) -> None:
    service = _service(tmp_path)
    draft = service.interpret(
        user_id=USER,
        project_id=PROJECT,
        prompt="30 x 50 ft, road on east, 2 BHK",
        references=(),
    )
    store = RequirementsStore(tmp_path)
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
    store.save_confirmed(confirmed)

    def failed_replace(source: str | Path, destination: str | Path) -> None:
        assert Path(source).exists()
        assert Path(destination).exists()
        raise OSError("simulated atomic replacement failure")

    monkeypatch.setattr("ai_vastu.requirements.store.os.replace", failed_replace)
    with pytest.raises(OSError, match="simulated atomic replacement failure"):
        if record_kind == "draft":
            store.save_draft(draft.model_copy(update={"prompt": "new prompt"}))
        else:
            store.save_confirmed(confirmed.model_copy(update={"parking_count": 2}))

    assert store.get_draft(draft.draft_id) == draft
    assert store.get_confirmed(draft.draft_id) == confirmed
    assert not list(tmp_path.glob("*.tmp"))
