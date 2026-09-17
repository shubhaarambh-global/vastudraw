from __future__ import annotations

from ai_vastu.generation import (
    CirculationGenerationConfig,
    GenerationDisposition,
    generate_architectural_plan,
)
from ai_vastu.plan_schema import OpeningKind

from .test_pipeline import _request


def test_auto_circulation_and_clearance_reserve_can_pass_validation() -> None:
    base = _request()
    request = base.model_copy(
        update={
            "planner_config": base.planner_config.model_copy(
                update={
                    "solver_step_mm": 10,
                    "clearance_reserve_mm": 230,
                }
            ),
            "circulation_config": CirculationGenerationConfig(
                auto_generate=True,
                internal_door_width_mm=800,
                external_door_width_mm=900,
                edge_margin_mm=100,
                door_height_mm=2100,
            ),
        }
    )

    first = generate_architectural_plan(request)
    second = generate_architectural_plan(request)

    assert first == second
    assert first.content_hash == second.content_hash
    assert first.disposition is GenerationDisposition.ACCEPTED
    assert first.validation_result is not None
    assert first.validation_result.report.valid is True
    assert first.validation_result.report.errors == ()
    assert first.geometry_result is not None
    openings = first.geometry_result.floor.openings
    assert len(openings) >= 2
    assert all(opening.kind is OpeningKind.DOOR for opening in openings)
