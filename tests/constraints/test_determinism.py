from ai_vastu.constraints import compile_constraints

from .helpers import compiler_input, dining_requirement, kitchen_requirement


def test_requirement_input_order_does_not_change_problem_hash() -> None:
    first = compile_constraints(
        compiler_input(requirements=(kitchen_requirement(), dining_requirement()))
    )
    second = compile_constraints(
        compiler_input(requirements=(dining_requirement(), kitchen_requirement()))
    )

    assert first.content_hash == second.content_hash
    assert first.room_instances == second.room_instances
    assert first.hard_constraints == second.hard_constraints
    assert first.soft_constraints == second.soft_constraints


def test_repeated_compilation_is_byte_deterministic() -> None:
    source = compiler_input(with_assumption=True)
    first = compile_constraints(source)
    second = compile_constraints(source)

    assert first.canonical_content_bytes() == second.canonical_content_bytes()
    assert first.content_hash == second.content_hash


def test_compiler_does_not_invent_assumptions() -> None:
    without = compile_constraints(compiler_input(with_assumption=False))
    with_one = compile_constraints(compiler_input(with_assumption=True))

    assert without.assumptions == ()
    assert len(with_one.assumptions) == 1
    assert with_one.assumptions[0].code == "TEST-ASSUMPTION"
