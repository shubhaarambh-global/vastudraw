from ai_vastu.constraints import (
    AdjacencyPreferenceObjective,
    AvailableFloorsConstraint,
    HardConstraintKind,
    SoftConstraintKind,
    compile_constraints,
)

from .helpers import compiler_input, kitchen_requirement


def test_quantity_expands_to_stable_room_instances() -> None:
    base = compiler_input(requirements=(kitchen_requirement(quantity=2),))
    # The kitchen preference references dining, so remove it for this isolated quantity test.
    requirement = base.room_requirements[0].model_copy(update={"adjacency_preferences": ()})
    result = compile_constraints(base.model_copy(update={"room_requirements": (requirement,)}))

    assert len(result.room_instances) == 2
    assert {item.ordinal for item in result.room_instances} == {1, 2}
    assert len({item.id for item in result.room_instances}) == 2


def test_compiler_emits_hard_and_soft_constraints_separately() -> None:
    result = compile_constraints(compiler_input())

    hard_kinds = {item.kind for item in result.hard_constraints}
    soft_kinds = {item.kind for item in result.soft_constraints}
    assert HardConstraintKind.CONTAINMENT in hard_kinds
    assert HardConstraintKind.MIN_DIMENSION in hard_kinds
    assert HardConstraintKind.MIN_AREA in hard_kinds
    assert HardConstraintKind.AVAILABLE_FLOORS in hard_kinds
    assert SoftConstraintKind.PREFERRED_DIMENSION in soft_kinds
    assert SoftConstraintKind.PREFERRED_AREA in soft_kinds
    assert SoftConstraintKind.FLOOR_PREFERENCE in soft_kinds
    assert SoftConstraintKind.ADJACENCY_PREFERENCE in soft_kinds
    assert SoftConstraintKind.ROOM_PRIORITIES in soft_kinds


def test_floor_constraint_contains_only_available_floors() -> None:
    result = compile_constraints(compiler_input(floors=(2, 0, 1)))
    floor_constraints = [
        item for item in result.hard_constraints if isinstance(item, AvailableFloorsConstraint)
    ]

    assert result.available_floor_indices == (0, 1, 2)
    assert floor_constraints
    assert all(item.allowed_floor_indices == (0, 1, 2) for item in floor_constraints)


def test_adjacency_preference_keeps_explicit_weight_and_geometry_thresholds() -> None:
    result = compile_constraints(compiler_input())
    adjacency = [
        item for item in result.soft_constraints if isinstance(item, AdjacencyPreferenceObjective)
    ]

    assert len(adjacency) == 1
    assert adjacency[0].weight == 90
    assert adjacency[0].max_gap_mm == 300
    assert adjacency[0].min_shared_length_mm == 1_200


def test_compiler_returns_content_hash() -> None:
    result = compile_constraints(compiler_input())

    assert result.content_hash is not None
    assert result.content_hash == result.compute_content_hash()
