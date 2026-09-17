from uuid import UUID

from ai_vastu.plan_intake import (
    PlanAuditStatus,
    PlanEnvelopeObservation,
    PlanObservationSource,
    PlanOrientationObservation,
    PlanRecognitionDraft,
    PlanRoomObservation,
    audit_recognized_plan,
)

PROJECT_ID = UUID("30000000-0000-0000-0000-000000000265")
INTAKE_ID = UUID("40000000-0000-0000-0000-000000000265")


def recognition(*, north: float | None = 0.0) -> PlanRecognitionDraft:
    return PlanRecognitionDraft(
        project_id=PROJECT_ID,
        intake_id=INTAKE_ID,
        provider="fixture",
        model=None,
        reference_names=("plan.png",),
        envelope=PlanEnvelopeObservation(
            geometry_type="RECTANGLE",
            width_mm=9144,
            depth_mm=15240,
            built_up_area_mm2=9144 * 15240,
            confidence=0.9,
            source=PlanObservationSource.IMAGE,
            requires_confirmation=True,
        ),
        orientation=PlanOrientationObservation(
            north_rotation_deg=north,
            confidence=0.9 if north is not None else 0.0,
            source=PlanObservationSource.IMAGE,
            requires_confirmation=True,
        ),
        rooms=(
            PlanRoomObservation(
                room_type="kitchen",
                centroid_x_basis_points=8000,
                centroid_y_basis_points=2000,
                confidence=0.9,
                source=PlanObservationSource.IMAGE,
            ),
            PlanRoomObservation(
                room_type="puja",
                centroid_x_basis_points=8000,
                centroid_y_basis_points=8000,
                confidence=0.9,
                source=PlanObservationSource.IMAGE,
            ),
            PlanRoomObservation(
                room_type="master_bedroom",
                centroid_x_basis_points=2000,
                centroid_y_basis_points=2000,
                confidence=0.9,
                source=PlanObservationSource.IMAGE,
            ),
            PlanRoomObservation(
                room_type="living",
                centroid_x_basis_points=8000,
                centroid_y_basis_points=6500,
                confidence=0.9,
                source=PlanObservationSource.IMAGE,
            ),
            PlanRoomObservation(
                room_type="common_toilet",
                centroid_x_basis_points=2000,
                centroid_y_basis_points=7000,
                confidence=0.9,
                source=PlanObservationSource.IMAGE,
            ),
        ),
    ).with_content_hash()


def test_uploaded_plan_receives_provisional_soft_vastu_score() -> None:
    audit = audit_recognized_plan(recognition())

    assert audit.status is PlanAuditStatus.SCORED
    assert audit.overall_basis_points is not None
    assert audit.provisional is True
    assert audit.evaluation_coverage_basis_points is not None
    assert 0 < audit.evaluation_coverage_basis_points < 10_000
    assert audit.evaluated_weight > 0
    assert audit.unevaluated_weight > 0

    by_id = {item.rule_id: item for item in audit.rules}
    assert by_id["SOFT_KITCHEN_ZONE"].status == "PREFERRED"
    assert by_id["SOFT_PUJA_ZONE"].status == "PREFERRED"
    assert by_id["SOFT_MASTER_BEDROOM_ZONE"].status == "PREFERRED"
    assert by_id["SOFT_STAIRCASE_ZONE"].status == "NOT_APPLICABLE"


def test_uploaded_plan_never_fabricates_score_without_true_north() -> None:
    audit = audit_recognized_plan(recognition(north=None))

    assert audit.status is PlanAuditStatus.NEEDS_ORIENTATION
    assert audit.overall_basis_points is None
    assert audit.suggestions
