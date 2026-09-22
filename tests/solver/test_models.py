from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from ai_vastu.solver import CirculationRepairPair, PlannerConfig


def test_solver_config_requires_single_worker() -> None:
    with pytest.raises(ValidationError):
        PlannerConfig(
            solver_step_mm=100,
            max_time_ms=1000,
            max_conflicts=1000,
            random_seed=1,
            num_search_workers=2,  # type: ignore[arg-type]
        )


def test_solver_config_rejects_nonpositive_step() -> None:
    with pytest.raises(ValidationError):
        PlannerConfig(
            solver_step_mm=0,
            max_time_ms=1000,
            max_conflicts=1000,
        )


def test_circulation_repair_pair_requires_distinct_rooms() -> None:
    room_id = UUID(int=1)
    with pytest.raises(ValidationError):
        CirculationRepairPair(
            first_room_id=room_id,
            second_room_id=room_id,
            min_shared_length_mm=1_000,
        )
