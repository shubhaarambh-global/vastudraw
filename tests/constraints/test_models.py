import pytest
from pydantic import ValidationError

from ai_vastu.constraints import (
    CompiledConstraintProblem,
    ConstraintCompilerInput,
    compile_constraints,
)

from .helpers import compiler_input


def test_available_floor_indices_must_be_unique() -> None:
    payload = compiler_input().model_dump()
    payload["available_floor_indices"] = (0, 0)

    with pytest.raises(ValidationError, match="must be unique"):
        ConstraintCompilerInput.model_validate(payload)


def test_compiled_problem_hash_tampering_is_rejected() -> None:
    problem = compile_constraints(compiler_input())
    payload = problem.model_dump()
    payload["content_hash"] = "0" * 64

    with pytest.raises(ValidationError, match="does not match"):
        CompiledConstraintProblem.model_validate(payload)
