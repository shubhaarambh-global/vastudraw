from __future__ import annotations

from pathlib import Path
from uuid import UUID

from .errors import PlanAnalysisNotFoundError
from .models import (
    PlanAnalysisResult,
    PlanGeometryConfirmationInput,
    PlanGeometryConfirmationRecord,
)


class PlanAnalysisStore:
    def __init__(self, generation_intake_root: Path) -> None:
        self._root = generation_intake_root.resolve()

    def _intake_dir(self, project_id: UUID, intake_id: UUID) -> Path:
        return self._root / str(project_id) / str(intake_id)

    def save_analysis(self, result: PlanAnalysisResult) -> PlanAnalysisResult:
        path = self._intake_dir(result.project_id, result.intake_id)
        if not path.is_dir():
            raise PlanAnalysisNotFoundError(f"Generation intake {result.intake_id} does not exist.")
        final = result.with_content_hash()
        (path / "plan-analysis.json").write_text(
            final.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return final

    def get_analysis(self, project_id: UUID, intake_id: UUID) -> PlanAnalysisResult:
        path = self._intake_dir(project_id, intake_id) / "plan-analysis.json"
        if not path.is_file():
            raise PlanAnalysisNotFoundError(f"Plan analysis does not exist for intake {intake_id}.")
        return PlanAnalysisResult.model_validate_json(path.read_text(encoding="utf-8"))

    def save_confirmation(
        self,
        project_id: UUID,
        intake_id: UUID,
        confirmation: PlanGeometryConfirmationInput,
    ) -> PlanGeometryConfirmationRecord:
        path = self._intake_dir(project_id, intake_id)
        if not path.is_dir():
            raise PlanAnalysisNotFoundError(f"Generation intake {intake_id} does not exist.")
        record = PlanGeometryConfirmationRecord(
            project_id=project_id,
            intake_id=intake_id,
            width_mm=confirmation.width_mm,
            depth_mm=confirmation.depth_mm,
            exact_area_mm2=confirmation.width_mm * confirmation.depth_mm,
            north_rotation_deg=confirmation.north_rotation_deg,
            road_side=confirmation.road_side,
            entrance_facing=confirmation.entrance_facing,
            preserve_outer_envelope=True,
            confirmed_by_user=True,
        ).with_content_hash()
        (path / "plan-confirmation.json").write_text(
            record.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return record

    def get_confirmation(
        self,
        project_id: UUID,
        intake_id: UUID,
    ) -> PlanGeometryConfirmationRecord:
        path = self._intake_dir(project_id, intake_id) / "plan-confirmation.json"
        if not path.is_file():
            raise PlanAnalysisNotFoundError(
                f"Plan geometry confirmation does not exist for intake {intake_id}."
            )
        return PlanGeometryConfirmationRecord.model_validate_json(path.read_text(encoding="utf-8"))
