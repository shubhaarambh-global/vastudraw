from __future__ import annotations

from ai_vastu.architectural_geometry import (
    ArchitecturalGeometryError,
    ArchitecturalGeometryRequest,
    build_architectural_geometry,
)
from ai_vastu.constraints import (
    ConstraintCompilerError,
    ConstraintCompilerInput,
    compile_constraints,
)
from ai_vastu.solver import PlannerError, PlannerStatus, solve_rectangular_problem
from ai_vastu.validation import (
    ArchitecturalValidationRequest,
    validate_architectural_geometry,
)

from .errors import GenerationInputError
from .models import (
    ArchitecturalGenerationRequest,
    ArchitecturalGenerationResult,
    GenerationDisposition,
)


def generate_architectural_plan(
    request: ArchitecturalGenerationRequest,
) -> ArchitecturalGenerationResult:
    """Run the deterministic architectural pipeline without inventing Vastu semantics.

    Phase 16 deliberately orchestrates only the already-validated architectural engine.
    Vastu rules remain outside this workflow until Vastu Specification v1 is reviewed,
    frozen and cryptographically pinned.
    """

    try:
        problem = compile_constraints(
            ConstraintCompilerInput(
                buildable_area=request.buildable_area,
                available_floor_indices=(request.floor_index,),
                room_requirements=request.room_requirements,
                assumptions=request.assumptions,
            )
        )
        planner_result = solve_rectangular_problem(
            problem,
            config=request.planner_config,
        )
    except (ConstraintCompilerError, PlannerError, ValueError) as exc:
        raise GenerationInputError(str(exc)) from exc

    if planner_result.status not in (PlannerStatus.OPTIMAL, PlannerStatus.FEASIBLE):
        return ArchitecturalGenerationResult(
            disposition=GenerationDisposition.UNSOLVED,
            problem=problem,
            planner_result=planner_result,
        ).with_content_hash()

    try:
        geometry_result = build_architectural_geometry(
            ArchitecturalGeometryRequest(
                problem=problem,
                planner_result=planner_result,
                floor_id=request.floor_id,
                floor_name=request.floor_name,
                elevation_mm=request.elevation_mm,
                floor_to_floor_mm=request.floor_to_floor_mm,
                wall_config=request.wall_config,
                openings=request.openings,
                stairs=request.stairs,
            )
        )
        validation_result = validate_architectural_geometry(
            ArchitecturalValidationRequest(
                plot_boundary=request.plot_boundary,
                problem=problem,
                geometry=geometry_result,
                config=request.validation_config,
                swing_contexts=request.swing_contexts,
            )
        )
    except (ArchitecturalGeometryError, ValueError) as exc:
        raise GenerationInputError(str(exc)) from exc

    disposition = (
        GenerationDisposition.ACCEPTED
        if validation_result.report.valid
        else GenerationDisposition.REJECTED
    )
    return ArchitecturalGenerationResult(
        disposition=disposition,
        problem=problem,
        planner_result=planner_result,
        geometry_result=geometry_result,
        validation_result=validation_result,
    ).with_content_hash()
