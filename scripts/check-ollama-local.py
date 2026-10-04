from __future__ import annotations

import io
from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas

from ai_vastu.ollama_local_http import (
    OLLAMA_LOCAL_MODEL,
    OllamaLocalClient,
    OllamaLocalRequestError,
)
from ai_vastu.plan_intake import (
    PlanIntakeService,
    PlanRecognitionDraft,
    PlanRecognitionInput,
    PlanReferenceBlob,
    PlanReferenceKind,
    create_plan_intake_service,
)
from ai_vastu.requirements import RequirementsService
from ai_vastu.requirements.models import EvidenceSource, RequirementDraft
from ai_vastu.requirements.providers import ReferenceAsset
from ai_vastu.requirements.service import create_provider
from ai_vastu.requirements.store import RequirementsStore

PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")
INTAKE_IDS = {
    "PNG": UUID("33333333-3333-3333-3333-333333333331"),
    "JPEG": UUID("33333333-3333-3333-3333-333333333332"),
    "PDF-PATH": UUID("33333333-3333-3333-3333-333333333333"),
}
EXPECTED_ROOMS = {"living", "kitchen", "bedroom", "toilet"}


class _QualificationRequirementsStore:
    """Minimal non-persistent store for the live provider/service qualification."""

    def __init__(self) -> None:
        self.saved: RequirementDraft | None = None

    def save_draft(self, draft: RequirementDraft) -> None:
        self.saved = draft


class QualificationAssertionError(RuntimeError):
    def __init__(self, code: str, *, details: tuple[str, ...] = ()) -> None:
        self.code = code
        self.details = details
        super().__init__("Qualification assertion failed.")


def _font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _plan_image(format_name: str) -> bytes:
    output = io.BytesIO()
    with Image.new("RGB", (1000, 1400), "white") as image:
        draw = ImageDraw.Draw(image)
        title = _font(52)
        label = _font(42)
        draw.text((400, 30), "NORTH", fill="black", font=title)
        draw.polygon(((500, 105), (470, 170), (530, 170)), fill="black")
        draw.rectangle((80, 210, 920, 1320), outline="black", width=12)
        draw.line((500, 210, 500, 1320), fill="black", width=8)
        draw.line((80, 650, 920, 650), fill="black", width=8)
        draw.line((80, 980, 920, 980), fill="black", width=8)
        draw.text((170, 400), "LIVING", fill="black", font=label)
        draw.text((610, 400), "KITCHEN", fill="black", font=label)
        draw.text((150, 800), "BEDROOM", fill="black", font=label)
        draw.text((650, 800), "TOILET", fill="black", font=label)
        draw.text((360, 1130), "ENTRY", fill="black", font=label)
        save_options: dict[str, object] = {}
        if format_name == "JPEG":
            save_options = {"quality": 95, "subsampling": 0}
        image.save(output, format=format_name, **save_options)
    return output.getvalue()


def _plan_pdf() -> bytes:
    output = io.BytesIO()
    document = canvas.Canvas(output, pagesize=(500, 700), invariant=True)
    document.setFont("Helvetica-Bold", 22)
    document.drawCentredString(250, 665, "NORTH")
    document.line(250, 640, 250, 610)
    document.line(250, 640, 240, 620)
    document.line(250, 640, 260, 620)
    document.rect(40, 40, 420, 550)
    document.line(250, 40, 250, 590)
    document.line(40, 370, 460, 370)
    document.line(40, 205, 460, 205)
    document.setFont("Helvetica-Bold", 18)
    document.drawString(90, 475, "LIVING")
    document.drawString(305, 475, "KITCHEN")
    document.drawString(75, 285, "BEDROOM")
    document.drawString(320, 285, "TOILET")
    document.drawCentredString(250, 110, "ENTRY")
    document.showPage()
    document.save()
    return output.getvalue()


def _assert_requirements(draft: RequirementDraft) -> RequirementDraft:
    if draft.provider != "ollama_local" or draft.model != OLLAMA_LOCAL_MODEL:
        raise QualificationAssertionError("requirements_provenance_mismatch")
    if draft.schema_version != "24A.1":
        raise QualificationAssertionError("requirements_schema_mismatch")
    if draft.plot_width_mm is None or draft.plot_depth_mm is None:
        raise QualificationAssertionError("requirements_dimensions_missing")
    if draft.bedroom_count is None or draft.bedroom_count.value != 2:
        raise QualificationAssertionError("requirements_bedroom_count_mismatch")
    proposed = (
        draft.plot_width_mm,
        draft.plot_depth_mm,
        draft.north_rotation_deg,
        draft.road_side,
        draft.entrance_facing,
        draft.floor_count,
        draft.bedroom_count,
        draft.parking_count,
    )
    if any(item is not None and not item.requires_confirmation for item in proposed):
        raise QualificationAssertionError("requirements_confirmation_boundary")
    if any(
        item is not None and item.source is EvidenceSource.USER_CONFIRMED
        for item in proposed
    ):
        raise QualificationAssertionError("requirements_source_boundary")
    return draft


def _recognized_text(draft: PlanRecognitionDraft) -> str:
    values: list[str] = [*draft.observations]
    values.extend(draft.orientation.evidence)
    for room in draft.rooms:
        values.extend((room.room_type, room.label or "", *room.evidence))
    return " ".join(values).lower()


def _assert_plan(
    draft: PlanRecognitionDraft,
    *,
    reference_name: str,
) -> PlanRecognitionDraft:
    if draft.provider != "ollama_local" or draft.model != OLLAMA_LOCAL_MODEL:
        raise QualificationAssertionError("plan_provenance_mismatch")
    if draft.schema_version != "26B.5.1":
        raise QualificationAssertionError("plan_schema_mismatch")
    if draft.reference_names != (reference_name,):
        raise QualificationAssertionError("plan_reference_names_mismatch")
    if draft.content_hash is None:
        raise QualificationAssertionError("plan_content_hash_absent")
    if draft.content_hash != draft.compute_content_hash():
        raise QualificationAssertionError("plan_content_hash_mismatch")
    observations = (draft.envelope, draft.orientation, *draft.rooms)
    if any(not item.requires_confirmation for item in observations):
        raise QualificationAssertionError("plan_confirmation_boundary")
    if any(item.source.value == "USER_CONFIRMED" for item in observations):
        raise QualificationAssertionError("plan_source_boundary")
    recognized = _recognized_text(draft)
    if draft.orientation.north_rotation_deg is None and "north" not in recognized:
        raise QualificationAssertionError("plan_north_missing")
    missing = {token for token in EXPECTED_ROOMS if token not in recognized}
    if missing:
        raise QualificationAssertionError(
            "plan_required_room_missing",
            details=tuple(sorted(missing)),
        )
    return draft


def _recognize(
    service: PlanIntakeService,
    *,
    kind_label: str,
    filename: str,
    content_type: str,
    kind: PlanReferenceKind,
    data: bytes,
) -> PlanRecognitionDraft:
    return _assert_plan(
        service.recognize(
            PlanRecognitionInput(
                project_id=PROJECT_ID,
                intake_id=INTAKE_IDS[kind_label],
                prompt=(
                    "Recognize the visible NORTH arrow and room labels LIVING, "
                    "KITCHEN, BEDROOM, and TOILET. Do not invent dimensions."
                ),
                references=(
                    PlanReferenceBlob(
                        filename=filename,
                        content_type=content_type,
                        kind=kind,
                        data=data,
                    ),
                ),
            )
        ),
        reference_name=filename,
    )


def _strict_json_probe(client: OllamaLocalClient) -> dict[str, str]:
    schema = {
        "type": "object",
        "properties": {"status": {"const": "PASS_LOCAL", "type": "string"}},
        "required": ["status"],
        "additionalProperties": False,
    }

    def validate(payload: dict[str, Any], _model: str) -> dict[str, str]:
        if payload != {"status": "PASS_LOCAL"}:
            raise ValueError
        return {"status": "PASS_LOCAL"}

    return client.complete_validated_json(
        messages=(
            {
                "role": "user",
                "content": "Return the status required by the supplied schema.",
            },
        ),
        schema=schema,
        validator=validate,
        max_tokens=32,
    )


def _find_ollama_error(exc: BaseException) -> OllamaLocalRequestError | None:
    current: BaseException | None = exc
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            return None
        seen.add(id(current))
        if isinstance(current, OllamaLocalRequestError):
            return current
        current = current.__cause__ or current.__context__
    return None


def _run[T](label: str, probe: Callable[[], T]) -> T | None:
    try:
        result = probe()
    except Exception as exc:
        if isinstance(exc, QualificationAssertionError):
            detail = ",".join(exc.details)
            suffix = f" details={detail}" if detail else ""
            print(f"{label} FAIL reason={exc.code}{suffix}")
            return None
        ollama_error = _find_ollama_error(exc)
        if ollama_error is not None:
            fields = [
                f"category={ollama_error.category.value}",
                f"stage={ollama_error.stage.value}",
                f"attempts={ollama_error.attempts}",
            ]
            if ollama_error.http_status is not None:
                fields.append(f"http_status={ollama_error.http_status}")
            if ollama_error.timeout_kind is not None:
                fields.append(f"timeout_kind={ollama_error.timeout_kind.value}")
            if ollama_error.validation_issues:
                validation = ",".join(
                    f"{issue.location}:{issue.error_type}"
                    for issue in ollama_error.validation_issues
                )
                fields.append(f"validation={validation}")
            print(f"{label} FAIL {' '.join(fields)}")
            return None
        print(f"{label} FAIL error={type(exc).__name__}")
        return None
    print(f"{label} PASS_LOCAL")
    return result


def main() -> None:
    results: dict[str, object] = {}
    statuses: dict[str, bool] = {}

    def stage(label: str, probe: Callable[[], object]) -> None:
        result = _run(label, probe)
        statuses[label] = result is not None
        if result is not None:
            results[label] = result

    def blocked(label: str, dependencies: tuple[str, ...]) -> None:
        print(f"{label} BLOCKED_DEPENDENCY missing={','.join(dependencies)}")
        statuses[label] = False

    stage(
        "OLLAMA ENDPOINT",
        lambda: OllamaLocalClient.from_environment().verify_endpoint(),
    )
    stage(
        "OLLAMA MODEL",
        lambda: OllamaLocalClient.from_environment().verify_pinned_model_available(),
    )

    def requirements_text() -> RequirementDraft:
        requirements_service = RequirementsService(
            create_provider(),
            cast(RequirementsStore, _QualificationRequirementsStore()),
        )
        return _assert_requirements(
            requirements_service.interpret(
                user_id=USER_ID,
                project_id=PROJECT_ID,
                prompt=(
                    "A 9000 mm wide by 15000 mm deep residential plot with a "
                    "north-side road, two bedrooms, one floor, and one-car parking."
                ),
                references=(
                    ReferenceAsset(
                        filename="client-brief.txt",
                        content_type="text/plain",
                        data=b"qualification reference name only",
                    ),
                ),
            )
        )

    stage(
        "REQUIREMENTS TEXT",
        requirements_text,
    )

    stage(
        "PLAN PNG",
        lambda: _recognize(
            create_plan_intake_service(),
            kind_label="PNG",
            filename="qualification-plan.png",
            content_type="image/png",
            kind=PlanReferenceKind.IMAGE,
            data=_plan_image("PNG"),
        ),
    )
    stage(
        "PLAN JPEG",
        lambda: _recognize(
            create_plan_intake_service(),
            kind_label="JPEG",
            filename="qualification-plan.jpg",
            content_type="image/jpeg",
            kind=PlanReferenceKind.IMAGE,
            data=_plan_image("JPEG"),
        ),
    )
    stage(
        "PLAN PDF-PATH",
        lambda: _recognize(
            create_plan_intake_service(),
            kind_label="PDF-PATH",
            filename="qualification-plan.pdf",
            content_type="application/pdf",
            kind=PlanReferenceKind.PDF,
            data=_plan_pdf(),
        ),
    )
    stage(
        "STRICT JSON",
        lambda: _strict_json_probe(OllamaLocalClient.from_environment()),
    )

    def provenance() -> bool:
        requirement = results.get("REQUIREMENTS TEXT")
        plans = [
            results.get("PLAN PNG"),
            results.get("PLAN JPEG"),
            results.get("PLAN PDF-PATH"),
        ]
        if not isinstance(requirement, RequirementDraft) or any(
            not isinstance(plan, PlanRecognitionDraft) for plan in plans
        ):
            raise RuntimeError
        if requirement.provider != "ollama_local" or requirement.model != OLLAMA_LOCAL_MODEL:
            raise RuntimeError
        if any(
            plan.provider != "ollama_local" or plan.model != OLLAMA_LOCAL_MODEL
            for plan in plans
            if isinstance(plan, PlanRecognitionDraft)
        ):
            raise RuntimeError
        return True

    provenance_dependencies = tuple(
        label
        for label in ("REQUIREMENTS TEXT", "PLAN PNG", "PLAN JPEG", "PLAN PDF-PATH")
        if label not in results
    )
    if provenance_dependencies:
        blocked("PROVENANCE", provenance_dependencies)
    else:
        stage("PROVENANCE", provenance)

    def content_hashes() -> bool:
        plans = [
            results.get("PLAN PNG"),
            results.get("PLAN JPEG"),
            results.get("PLAN PDF-PATH"),
        ]
        if any(not isinstance(plan, PlanRecognitionDraft) for plan in plans):
            raise RuntimeError
        if any(
            plan.content_hash != plan.compute_content_hash()
            for plan in plans
            if isinstance(plan, PlanRecognitionDraft)
        ):
            raise RuntimeError
        return True

    content_hash_dependencies = tuple(
        label
        for label in ("PLAN PNG", "PLAN JPEG", "PLAN PDF-PATH")
        if label not in results
    )
    if content_hash_dependencies:
        blocked("CONTENT HASH", content_hash_dependencies)
    else:
        stage("CONTENT HASH", content_hashes)

    required = (
        "OLLAMA ENDPOINT",
        "OLLAMA MODEL",
        "REQUIREMENTS TEXT",
        "PLAN PNG",
        "PLAN JPEG",
        "PLAN PDF-PATH",
        "STRICT JSON",
        "PROVENANCE",
        "CONTENT HASH",
    )
    if not all(statuses.get(label, False) for label in required):
        raise SystemExit("OLLAMA LOCAL QUALIFICATION FAIL")
    print("OLLAMA LOCAL QUALIFICATION PASS_LOCAL")


if __name__ == "__main__":
    try:
        main()
    except OllamaLocalRequestError as exc:
        raise SystemExit(
            "OLLAMA LOCAL QUALIFICATION FAIL "
            f"category={exc.category.value} stage={exc.stage.value}"
        ) from None
    except Exception as exc:
        raise SystemExit(
            f"OLLAMA LOCAL QUALIFICATION FAIL error={type(exc).__name__}"
        ) from None
