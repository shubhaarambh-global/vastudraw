from __future__ import annotations

import hashlib

from ai_vastu.exporting import DrawingScene, DxfExportConfig, ExportArtifact, render_dxf
from ai_vastu.exporting.geometry import opening_segments, scene_bounds, visible_wall_segments

from .backend import DwgBackend
from .errors import DwgBackendNotQualifiedError, DwgInspectionError
from .models import (
    DwgExtents,
    DwgQualificationConfig,
    DwgQualificationReport,
    DwgSemanticFingerprint,
)

_DWG_SIGNATURE_PREFIX = b"AC10"


def expected_fingerprint(scene: DrawingScene) -> DwgSemanticFingerprint:
    bounds = scene_bounds(scene)
    return DwgSemanticFingerprint(
        room_count=len(scene.rooms),
        wall_segment_count=len(visible_wall_segments(scene)),
        opening_count=len(opening_segments(scene)),
        dimension_count=len(scene.dimensions),
        stair_count=len(scene.stairs),
        extents=DwgExtents(
            min_x_mm=bounds.min_x_mm,
            min_y_mm=bounds.min_y_mm,
            max_x_mm=bounds.max_x_mm,
            max_y_mm=bounds.max_y_mm,
        ),
    )


def _extent_failures(
    expected: DwgExtents,
    actual: DwgExtents,
    tolerance_mm: float,
) -> list[str]:
    values = (
        ("min_x_mm", expected.min_x_mm, actual.min_x_mm),
        ("min_y_mm", expected.min_y_mm, actual.min_y_mm),
        ("max_x_mm", expected.max_x_mm, actual.max_x_mm),
        ("max_y_mm", expected.max_y_mm, actual.max_y_mm),
    )
    return [
        f"EXTENT_MISMATCH:{name}"
        for name, expected_value, actual_value in values
        if abs(expected_value - actual_value) > tolerance_mm
    ]


def qualify_backend(
    scene: DrawingScene,
    backend: DwgBackend,
    config: DwgQualificationConfig | None = None,
) -> DwgQualificationReport:
    config = config or DwgQualificationConfig()
    if scene.scene_hash is None:
        scene = scene.with_scene_hash()
    assert scene.scene_hash is not None
    capabilities = backend.capabilities
    failures: list[str] = []

    if capabilities.test_backend:
        failures.append("TEST_BACKEND_NOT_PRODUCTION")
    if not capabilities.production_eligible:
        failures.append("BACKEND_NOT_PRODUCTION_ELIGIBLE")
    if not capabilities.modern_dwg_write:
        failures.append("BACKEND_CANNOT_WRITE_MODERN_DWG")
    if not capabilities.roundtrip_inspection:
        failures.append("BACKEND_CANNOT_ROUNDTRIP_INSPECT")
    if config.target_version not in capabilities.supported_targets:
        failures.append("TARGET_VERSION_NOT_SUPPORTED")

    if failures:
        return DwgQualificationReport(
            backend_id=capabilities.backend_id,
            backend_version=capabilities.backend_version,
            target_version=config.target_version,
            source_scene_hash=scene.scene_hash,
            qualified=False,
            failures=tuple(sorted(set(failures))),
        ).with_report_hash()

    dxf = render_dxf(scene, DxfExportConfig())
    dwg_bytes = backend.convert_dxf(dxf.content, config.target_version)
    output_sha256 = hashlib.sha256(dwg_bytes).hexdigest()
    if not dwg_bytes.startswith(_DWG_SIGNATURE_PREFIX):
        failures.append("INVALID_DWG_SIGNATURE")

    try:
        inspection = backend.inspect(dwg_bytes)
    except Exception as exc:  # backend boundary must fail closed
        raise DwgInspectionError("DWG backend inspection failed.") from exc

    if inspection.units != "MM":
        failures.append("DWG_UNITS_NOT_MM")
    if config.require_scene_hash and inspection.scene_hash != scene.scene_hash:
        failures.append("SCENE_HASH_MISMATCH")
    required = set(config.required_layers)
    if not required.issubset(set(inspection.layers)):
        failures.append("REQUIRED_LAYER_MISSING")

    expected = expected_fingerprint(scene)
    actual = inspection.fingerprint
    if expected.room_count != actual.room_count:
        failures.append("ROOM_COUNT_MISMATCH")
    if expected.wall_segment_count != actual.wall_segment_count:
        failures.append("WALL_SEGMENT_COUNT_MISMATCH")
    if expected.opening_count != actual.opening_count:
        failures.append("OPENING_COUNT_MISMATCH")
    if config.require_dimensions and expected.dimension_count != actual.dimension_count:
        failures.append("DIMENSION_COUNT_MISMATCH")
    if expected.stair_count != actual.stair_count:
        failures.append("STAIR_COUNT_MISMATCH")
    failures.extend(_extent_failures(expected.extents, actual.extents, config.max_extent_delta_mm))

    return DwgQualificationReport(
        backend_id=capabilities.backend_id,
        backend_version=capabilities.backend_version,
        target_version=config.target_version,
        source_scene_hash=scene.scene_hash,
        output_sha256=output_sha256,
        qualified=not failures,
        failures=tuple(sorted(set(failures))),
        inspection=inspection,
    ).with_report_hash()


def export_qualified_dwg(
    scene: DrawingScene,
    backend: DwgBackend,
    qualification: DwgQualificationReport,
) -> ExportArtifact:
    if scene.scene_hash is None:
        scene = scene.with_scene_hash()
    assert scene.scene_hash is not None
    capabilities = backend.capabilities
    if not qualification.qualified:
        raise DwgBackendNotQualifiedError("DWG backend has not passed qualification.")
    if qualification.backend_id != capabilities.backend_id:
        raise DwgBackendNotQualifiedError(
            "Qualification backend identity does not match runtime backend."
        )
    if qualification.backend_version != capabilities.backend_version:
        raise DwgBackendNotQualifiedError(
            "Qualification backend version does not match runtime backend."
        )
    if qualification.source_scene_hash != scene.scene_hash:
        raise DwgBackendNotQualifiedError("Qualification report is not bound to this DrawingScene.")
    if capabilities.test_backend:
        raise DwgBackendNotQualifiedError("Test DWG backends cannot export production artifacts.")

    dxf = render_dxf(scene, DxfExportConfig())
    content = backend.convert_dxf(dxf.content, qualification.target_version)
    if not content.startswith(_DWG_SIGNATURE_PREFIX):
        raise DwgBackendNotQualifiedError("Runtime DWG output does not have a DWG signature.")
    inspection = backend.inspect(content)
    if inspection.scene_hash != scene.scene_hash:
        raise DwgBackendNotQualifiedError("Runtime DWG round-trip lost scene provenance.")

    return ExportArtifact.create(
        format="DWG",
        filename=f"floor-{scene.floor_index}-{scene.revision_id}.dwg",
        media_type="application/acad",
        content=content,
        scene_hash=scene.scene_hash,
    )
