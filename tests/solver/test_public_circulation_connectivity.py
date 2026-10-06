from types import SimpleNamespace
from uuid import UUID

import pytest
from ortools.sat.python import cp_model

from ai_vastu.plan_schema import RoomType
from ai_vastu.solver import ResidentialPlanningConfig
from ai_vastu.solver.rectangular_cp_sat import _append_hard_residential_circulation

from .helpers import compiled_problem, config, living_requirement


@pytest.mark.parametrize("second_row_y,expected", [(40, cp_model.INFEASIBLE),
                                                   (30, cp_model.OPTIMAL)])
def test_public_access_requires_one_connected_entry_network(second_row_y, expected):
    # Each of the two rows already has a public neighbor for every room. A 1m gap
    # between rows must still fail: per-room adjacency alone does not prove access.
    kinds = (RoomType.LIVING, RoomType.DINING, RoomType.KITCHEN, RoomType.LOBBY)
    requirements = tuple(living_requirement().model_copy(update={
        "id": UUID(int=100 + index), "room_type": kind, "adjacency_preferences": (),
    }) for index, kind in enumerate(kinds))
    problem = compiled_problem(requirements=requirements)
    fixed = {
        RoomType.LIVING: (0, 0), RoomType.DINING: (30, 0),
        RoomType.KITCHEN: (0, second_row_y), RoomType.LOBBY: (30, second_row_y),
    }
    room_vars = {}
    for room in problem.room_instances:
        x, y = fixed[room.room_type]
        room_vars[room.id] = SimpleNamespace(x=x, y=y, x_end=x + 30, y_end=y + 30)
    model = cp_model.CpModel()
    planner_config = config().model_copy(update={
        "residential_planning": ResidentialPlanningConfig(
            enabled=True, require_horizontal_circulation=True,
        ),
    })
    _append_hard_residential_circulation(
        model, problem, room_vars, config=planner_config,
        width_cells=100, depth_cells=80, notices=[],
    )
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = 2
    assert solver.solve(model) == expected
