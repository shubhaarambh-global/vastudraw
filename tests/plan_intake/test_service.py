from uuid import UUID

from ai_vastu.plan_intake import (
    PlanEnvelopeObservation,
    PlanIntakeService,
    PlanObservationSource,
    PlanOrientationObservation,
    PlanRecognitionDraft,
    PlanRecognitionInput,
)

PROJECT_ID = UUID("61000000-0000-0000-0000-000000000265")
INTAKE_ID = UUID("62000000-0000-0000-0000-000000000265")


class ParkingInferenceProvider:
    name = "fixture"

    def recognize(
        self,
        request: PlanRecognitionInput,
    ) -> PlanRecognitionDraft:
        return PlanRecognitionDraft(
            project_id=request.project_id,
            intake_id=request.intake_id,
            provider=self.name,
            model=None,
            reference_names=("plan.pdf",),
            envelope=PlanEnvelopeObservation(
                geometry_type="RECTANGLE",
                width_mm=7620,
                depth_mm=10973,
                confidence=0.9,
                source=PlanObservationSource.PDF,
                requires_confirmation=True,
            ),
            orientation=PlanOrientationObservation(
                north_rotation_deg=270.0,
                road_side=None,
                entrance_facing=None,
                confidence=0.9,
                source=PlanObservationSource.PDF,
                requires_confirmation=True,
            ),
            questions=(
                "Road side is not explicitly marked; entrance direction is "
                "inferred from parking but requires confirmation.",
            ),
        ).with_content_hash()


def test_missing_road_and_entrance_are_not_described_as_inferred() -> None:
    service = PlanIntakeService(ParkingInferenceProvider())

    result = service.recognize(
        PlanRecognitionInput(
            project_id=PROJECT_ID,
            intake_id=INTAKE_ID,
            prompt="Audit ground floor.",
            references=(),
        )
    )

    combined = " ".join(result.questions).lower()

    assert "inferred from parking" not in combined
    assert "road side is not explicitly established" in combined
    assert "entrance facing is not explicitly established" in combined
