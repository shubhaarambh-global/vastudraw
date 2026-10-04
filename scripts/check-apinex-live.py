from __future__ import annotations

import io
import os
from collections.abc import Callable
from typing import cast
from uuid import UUID

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas

from ai_vastu.apinex_http import (
    APINEX_API_BASE,
    APINEX_MODEL,
    ApinexClient,
    ApinexRequestError,
)
from ai_vastu.plan_intake import (
    PlanObservationSource,
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

PROJECT_ID = UUID("a1111111-1111-1111-1111-111111111111")
USER_ID = UUID("a2222222-2222-2222-2222-222222222222")
INTAKE_IDS = {
    "PNG": UUID("a3333333-3333-3333-3333-333333333331"),
    "JPEG": UUID("a3333333-3333-3333-3333-333333333332"),
    "PDF-PATH": UUID("a3333333-3333-3333-3333-333333333333"),
}
EXPECTED_ROOMS = {"living", "kitchen", "bedroom", "toilet"}
_PROVIDER_SELECTORS = (
    "AI_VASTU_REQUIREMENTS_PROVIDER",
    "AI_VASTU_ARCHITECT_PROVIDER",
    "AI_VASTU_VASTU_PROVIDER",
    "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER",
    "AI_VASTU_REVISION_PROVIDER",
    "AI_VASTU_PLAN_RECOGNITION_PROVIDER",
)


class _Store:
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
        options: dict[str, object] = {}
        if format_name == "JPEG":
            options = {"quality": 95, "subsampling": 0}
        image.save(output, format=format_name, **options)
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
    if draft.provider != "apinex" or draft.model != APINEX_MODEL:
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
    if any(item is not None and item.source is EvidenceSource.USER_CONFIRMED for item in proposed):
        raise QualificationAssertionError("requirements_source_boundary")
    return draft


def _assert_plan(draft: PlanRecognitionDraft, reference_name: str) -> PlanRecognitionDraft:
    if draft.provider != "apinex" or draft.model != APINEX_MODEL:
        raise QualificationAssertionError("plan_provenance_mismatch")
    if draft.schema_version != "26B.5.1":
        raise QualificationAssertionError("plan_schema_mismatch")
    if draft.reference_names != (reference_name,):
        raise QualificationAssertionError("plan_reference_names_mismatch")
    if draft.content_hash is None:
        raise QualificationAssertionError("plan_content_hash_absent")
    if draft.content_hash != draft.compute_content_hash():
        raise QualificationAssertionError("plan_content_hash_mismatch")
    items = (draft.envelope, draft.orientation, *draft.rooms)
    if any(not item.requires_confirmation for item in items):
        raise QualificationAssertionError("plan_confirmation_boundary")
    if any(item.source is PlanObservationSource.USER_CONFIRMED for item in items):
        raise QualificationAssertionError("plan_source_boundary")
    text = " ".join(
        [
            *draft.observations,
            *draft.orientation.evidence,
            *(
                value
                for room in draft.rooms
                for value in (room.room_type, room.label or "", *room.evidence)
            ),
        ]
    ).lower()
    missing = tuple(sorted(token for token in EXPECTED_ROOMS if token not in text))
    if missing:
        raise QualificationAssertionError("plan_required_room_missing", details=missing)
    if draft.orientation.north_rotation_deg is None and "north" not in text:
        raise QualificationAssertionError("plan_north_missing")
    return draft


def _recognize(
    label: str, filename: str, content_type: str, kind: PlanReferenceKind, data: bytes
) -> PlanRecognitionDraft:
    return _assert_plan(
        create_plan_intake_service().recognize(
            PlanRecognitionInput(
                project_id=PROJECT_ID,
                intake_id=INTAKE_IDS[label],
                prompt=(
                    "Recognize visible NORTH, LIVING, KITCHEN, BEDROOM, and TOILET. "
                    "Return raw JSON only with the exact schema and no extra keys."
                ),
                references=(PlanReferenceBlob(filename, content_type, kind, data),),
            )
        ),
        filename,
    )


def _find_error(exc: BaseException) -> ApinexRequestError | None:
    current: BaseException | None = exc
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            return None
        seen.add(id(current))
        if isinstance(current, ApinexRequestError):
            return current
        current = current.__cause__ or current.__context__
    return None


def _run[T](label: str, probe: Callable[[], T]) -> T | None:
    try:
        result = probe()
    except Exception as exc:
        if isinstance(exc, QualificationAssertionError):
            detail = f" details={','.join(exc.details)}" if exc.details else ""
            print(f"{label} FAIL reason={exc.code}{detail}")
            return None
        error = _find_error(exc)
        if error is not None:
            fields = [
                f"category={error.category.value}",
                f"stage={error.stage.value}",
                f"attempts={error.attempts}",
            ]
            if error.http_status is not None:
                fields.append(f"http_status={error.http_status}")
            if error.timeout_kind is not None:
                fields.append(f"timeout_kind={error.timeout_kind.value}")
            print(f"{label} FAIL {' '.join(fields)}")
            return None
        print(f"{label} FAIL error={type(exc).__name__}")
        return None
    print(f"{label} PASS_LIVE")
    return result


def main() -> None:
    if not os.environ.get("APINEX_API_KEY", "").strip():
        raise SystemExit("APINEX LIVE QUALIFICATION FAIL category=configuration")
    os.environ["APP_ENV"] = "development"
    for selector in _PROVIDER_SELECTORS:
        os.environ[selector] = "apinex"
    os.environ.update(
        {
            "AI_VASTU_APINEX_BASE_URL": APINEX_API_BASE,
            "AI_VASTU_APINEX_MODEL": APINEX_MODEL,
            "AI_VASTU_APINEX_CONNECT_TIMEOUT_SECONDS": "5",
            "AI_VASTU_APINEX_READ_TIMEOUT_SECONDS": "180",
            "AI_VASTU_APINEX_TOTAL_TIMEOUT_SECONDS": "240",
            "AI_VASTU_APINEX_WRITE_TIMEOUT_SECONDS": "30",
            "AI_VASTU_APINEX_POOL_TIMEOUT_SECONDS": "5",
        }
    )
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

    stage("APINEX ENDPOINT", lambda: ApinexClient.from_environment().verify_endpoint())
    stage(
        "APINEX MODEL INVENTORY",
        lambda: ApinexClient.from_environment().verify_pinned_model_available(),
    )

    def text_probe() -> str:
        value = ApinexClient.from_environment().complete_text(
            messages=({"role": "user", "content": "Reply exactly APINEX_GPT6_LUNA_OK"},),
            max_tokens=32,
        )
        if value != "APINEX_GPT6_LUNA_OK":
            raise QualificationAssertionError("text_exact_mismatch")
        return value

    stage("APINEX TEXT", text_probe)

    schema = {
        "type": "object",
        "properties": {
            "ok": {"const": True, "type": "boolean"},
            "role": {"const": "architectural_ai", "type": "string"},
        },
        "required": ["ok", "role"],
        "additionalProperties": False,
    }

    def structured_probe() -> dict[str, object]:
        expected: dict[str, object] = {"ok": True, "role": "architectural_ai"}
        return ApinexClient.from_environment().complete_validated_json(
            messages=({"role": "user", "content": "Return the exact schema result."},),
            schema=schema,
            validator=lambda value, _model: (
                value if value == expected else (_ for _ in ()).throw(ValueError())
            ),
            max_tokens=64,
        )

    stage("APINEX STRUCTURED TEXT", structured_probe)

    def requirements_probe() -> RequirementDraft:
        service = RequirementsService(create_provider(), cast(RequirementsStore, _Store()))
        return _assert_requirements(
            service.interpret(
                user_id=USER_ID,
                project_id=PROJECT_ID,
                prompt=(
                    "A 9000 mm wide by 15000 mm deep residential plot with a north-side "
                    "road, two bedrooms, one floor, and one-car parking."
                ),
                references=(ReferenceAsset("synthetic-brief.txt", "text/plain", b"synthetic"),),
            )
        )

    stage("REQUIREMENTS TEXT", requirements_probe)
    stage(
        "PLAN PNG",
        lambda: _recognize(
            "PNG", "synthetic-plan.png", "image/png", PlanReferenceKind.IMAGE, _plan_image("PNG")
        ),
    )
    stage(
        "PLAN JPEG",
        lambda: _recognize(
            "JPEG", "synthetic-plan.jpg", "image/jpeg", PlanReferenceKind.IMAGE, _plan_image("JPEG")
        ),
    )
    stage(
        "PLAN PDF-PATH",
        lambda: _recognize(
            "PDF-PATH", "synthetic-plan.pdf", "application/pdf", PlanReferenceKind.PDF, _plan_pdf()
        ),
    )
    stage("STRICT JSON", structured_probe)

    dependencies = tuple(
        label
        for label in ("REQUIREMENTS TEXT", "PLAN PNG", "PLAN JPEG", "PLAN PDF-PATH")
        if label not in results
    )
    if dependencies:
        blocked("PROVENANCE", dependencies)
    else:

        def provenance() -> bool:
            values = [
                results[label]
                for label in ("REQUIREMENTS TEXT", "PLAN PNG", "PLAN JPEG", "PLAN PDF-PATH")
            ]
            if any(
                getattr(value, "provider", None) != "apinex"
                or getattr(value, "model", None) != APINEX_MODEL
                for value in values
            ):
                raise QualificationAssertionError("provenance_mismatch")
            return True

        stage("PROVENANCE", provenance)

    hash_dependencies = tuple(
        label for label in ("PLAN PNG", "PLAN JPEG", "PLAN PDF-PATH") if label not in results
    )
    if hash_dependencies:
        blocked("CONTENT HASH", hash_dependencies)
    else:

        def hashes() -> bool:
            plans = cast(
                list[PlanRecognitionDraft],
                [results[label] for label in ("PLAN PNG", "PLAN JPEG", "PLAN PDF-PATH")],
            )
            if any(plan.content_hash != plan.compute_content_hash() for plan in plans):
                raise QualificationAssertionError("content_hash_mismatch")
            return True

        stage("CONTENT HASH", hashes)

    required = (
        "APINEX ENDPOINT",
        "APINEX MODEL INVENTORY",
        "APINEX TEXT",
        "APINEX STRUCTURED TEXT",
        "REQUIREMENTS TEXT",
        "PLAN PNG",
        "PLAN JPEG",
        "PLAN PDF-PATH",
        "STRICT JSON",
        "PROVENANCE",
        "CONTENT HASH",
    )
    if not all(statuses.get(label, False) for label in required):
        raise SystemExit("APINEX LIVE QUALIFICATION FAIL")
    print("APINEX LIVE QUALIFICATION PASS_LIVE")


if __name__ == "__main__":
    main()
