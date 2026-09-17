from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from .models import (
    GenerationAttachmentRecord,
    GenerationIntakeRecord,
    GenerationReferenceKind,
)

MAX_ATTACHMENTS = 8
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024
_ALLOWED_MEDIA_TYPES = {
    "image/jpeg": (GenerationReferenceKind.IMAGE, ".jpg", "image/jpeg"),
    "image/png": (GenerationReferenceKind.IMAGE, ".png", "image/png"),
    "application/pdf": (GenerationReferenceKind.PDF, ".pdf", "application/pdf"),
    "application/dxf": (GenerationReferenceKind.DXF, ".dxf", "application/dxf"),
    "application/x-dxf": (GenerationReferenceKind.DXF, ".dxf", "application/dxf"),
    "image/vnd.dxf": (GenerationReferenceKind.DXF, ".dxf", "application/dxf"),
    "application/dwg": (GenerationReferenceKind.DWG, ".dwg", "application/dwg"),
    "application/acad": (GenerationReferenceKind.DWG, ".dwg", "application/dwg"),
    "application/x-acad": (GenerationReferenceKind.DWG, ".dwg", "application/dwg"),
    "image/vnd.dwg": (GenerationReferenceKind.DWG, ".dwg", "application/dwg"),
}
_EXTENSION_TYPES = {
    ".jpg": (GenerationReferenceKind.IMAGE, ".jpg", "image/jpeg"),
    ".jpeg": (GenerationReferenceKind.IMAGE, ".jpg", "image/jpeg"),
    ".png": (GenerationReferenceKind.IMAGE, ".png", "image/png"),
    ".pdf": (GenerationReferenceKind.PDF, ".pdf", "application/pdf"),
    ".dxf": (GenerationReferenceKind.DXF, ".dxf", "application/dxf"),
    ".dwg": (GenerationReferenceKind.DWG, ".dwg", "application/dwg"),
}


class GenerationIntakeError(ValueError):
    pass


class GenerationIntakeNotFoundError(LookupError):
    pass


class GenerationIntakeStorageConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IncomingGenerationAttachment:
    original_filename: str
    media_type: str
    content: bytes


def _classify_attachment(
    filename: str,
    media_type: str,
) -> tuple[GenerationReferenceKind, str, str]:
    suffix = Path(filename).suffix.lower()
    by_extension = _EXTENSION_TYPES.get(suffix)
    normalized_media = media_type.lower().strip()

    if by_extension is not None:
        expected_kind, storage_suffix, canonical_media = by_extension
        by_media = _ALLOWED_MEDIA_TYPES.get(normalized_media)
        if by_media is not None and by_media[0] is not expected_kind:
            raise GenerationIntakeError(f"{filename}: file extension and media type disagree.")
        return expected_kind, storage_suffix, canonical_media

    by_media = _ALLOWED_MEDIA_TYPES.get(normalized_media)
    if by_media is not None:
        return by_media

    raise GenerationIntakeError(
        "Only JPEG, PNG, PDF, DXF, and DWG generation references are supported."
    )


def _verify_signature(kind: GenerationReferenceKind, content: bytes) -> None:
    if kind is GenerationReferenceKind.IMAGE:
        if content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG\r\n\x1a\n"):
            return
        raise GenerationIntakeError("Image attachment signature is not JPEG or PNG.")

    if kind is GenerationReferenceKind.PDF:
        if not content.startswith(b"%PDF-"):
            raise GenerationIntakeError("PDF attachment signature does not match file type.")
        return

    if kind is GenerationReferenceKind.DXF:
        prefix = content[:2048].lstrip()
        if prefix.startswith(b"AutoCAD Binary DXF") or b"SECTION" in prefix.upper():
            return
        raise GenerationIntakeError("DXF attachment signature does not look like DXF.")

    if kind is GenerationReferenceKind.DWG:
        if not content.startswith(b"AC10"):
            raise GenerationIntakeError("DWG attachment signature does not look like DWG.")
        return

    raise GenerationIntakeError("Unsupported attachment kind.")


class GenerationIntakeStore:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def create(
        self,
        project_id: UUID,
        prompt: str,
        attachments: tuple[IncomingGenerationAttachment, ...],
        *,
        created_at: datetime | None = None,
        intake_id: UUID | None = None,
    ) -> GenerationIntakeRecord:
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise GenerationIntakeError("Generation prompt must not be blank.")
        if len(normalized_prompt) > 12_000:
            raise GenerationIntakeError("Generation prompt exceeds 12,000 characters.")
        if len(attachments) > MAX_ATTACHMENTS:
            raise GenerationIntakeError(f"At most {MAX_ATTACHMENTS} attachments are allowed.")

        total_bytes = sum(len(item.content) for item in attachments)
        if total_bytes > MAX_TOTAL_BYTES:
            raise GenerationIntakeError("Combined attachment size exceeds 50 MiB.")

        resolved_intake_id = intake_id or uuid4()
        intake_dir = self._root / str(project_id) / str(resolved_intake_id)
        intake_dir.mkdir(parents=True, exist_ok=False)
        records: list[GenerationAttachmentRecord] = []

        try:
            for incoming in attachments:
                if len(incoming.content) == 0:
                    raise GenerationIntakeError("Attachments must not be empty.")
                if len(incoming.content) > MAX_FILE_BYTES:
                    raise GenerationIntakeError("Each attachment must be 20 MiB or smaller.")

                kind, suffix, canonical_media = _classify_attachment(
                    incoming.original_filename,
                    incoming.media_type,
                )
                _verify_signature(kind, incoming.content)

                attachment_id = uuid4()
                storage_name = f"{attachment_id}{suffix}"
                (intake_dir / storage_name).write_bytes(incoming.content)
                records.append(
                    GenerationAttachmentRecord(
                        attachment_id=attachment_id,
                        kind=kind,
                        original_filename=incoming.original_filename.strip() or "reference",
                        media_type=canonical_media,
                        size_bytes=len(incoming.content),
                        sha256=hashlib.sha256(incoming.content).hexdigest(),
                        storage_name=storage_name,
                    )
                )

            timestamp = created_at or datetime.now(UTC)
            provisional = GenerationIntakeRecord.model_construct(
                intake_id=resolved_intake_id,
                project_id=project_id,
                created_at=timestamp,
                prompt=normalized_prompt,
                attachments=tuple(records),
                authoritative_geometry=False,
                content_hash="",
            )
            record = GenerationIntakeRecord(
                intake_id=resolved_intake_id,
                project_id=project_id,
                created_at=timestamp,
                prompt=normalized_prompt,
                attachments=tuple(records),
                authoritative_geometry=False,
                content_hash=provisional.compute_content_hash(),
            )
            (intake_dir / "manifest.json").write_text(
                record.model_dump_json(indent=2),
                encoding="utf-8",
            )
            return record
        except Exception:
            for child in intake_dir.iterdir():
                if child.is_file():
                    child.unlink()
            intake_dir.rmdir()
            raise

    def list_for_project(self, project_id: UUID) -> tuple[GenerationIntakeRecord, ...]:
        project_dir = self._root / str(project_id)
        if not project_dir.exists():
            return ()
        records: list[GenerationIntakeRecord] = []
        for manifest in project_dir.glob("*/manifest.json"):
            records.append(GenerationIntakeRecord.model_validate_json(manifest.read_text("utf-8")))
        return tuple(sorted(records, key=lambda item: (item.created_at, str(item.intake_id))))

    def get(self, project_id: UUID, intake_id: UUID) -> GenerationIntakeRecord:
        manifest = self._root / str(project_id) / str(intake_id) / "manifest.json"
        if not manifest.exists():
            raise GenerationIntakeNotFoundError(
                f"Generation intake {intake_id} does not exist for project {project_id}."
            )
        return GenerationIntakeRecord.model_validate_json(manifest.read_text("utf-8"))

    def read_attachment(
        self,
        project_id: UUID,
        intake_id: UUID,
        attachment_id: UUID,
    ) -> tuple[GenerationAttachmentRecord, bytes]:
        record = self.get(project_id, intake_id)
        attachment = next(
            (item for item in record.attachments if item.attachment_id == attachment_id),
            None,
        )
        if attachment is None:
            raise GenerationIntakeNotFoundError(
                f"Attachment {attachment_id} does not exist for intake {intake_id}."
            )

        path = self._root / str(project_id) / str(intake_id) / attachment.storage_name
        if not path.is_file():
            raise GenerationIntakeNotFoundError(f"Attachment payload {attachment_id} is missing.")

        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != attachment.sha256:
            raise GenerationIntakeError(
                f"Attachment {attachment_id} failed its stored SHA-256 integrity check."
            )
        return attachment, data


def create_generation_intake_store_from_environment(
    environment: dict[str, str] | None = None,
) -> GenerationIntakeStore:
    env = os.environ if environment is None else environment
    configured = env.get("AI_VASTU_GENERATION_UPLOAD_ROOT", "").strip()
    app_env = env.get("APP_ENV", "development").strip().lower()
    if app_env == "production" and not configured:
        raise GenerationIntakeStorageConfigurationError(
            "AI_VASTU_GENERATION_UPLOAD_ROOT is required in production."
        )
    root = Path(configured) if configured else Path(".local/generation-intakes")
    if app_env == "production" and not root.is_absolute():
        raise GenerationIntakeStorageConfigurationError(
            "Production generation upload root must be an absolute persistent path."
        )
    return GenerationIntakeStore(root)
