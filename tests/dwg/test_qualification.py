from __future__ import annotations

import pytest

from ai_vastu.dwg import (
    DwgBackendNotQualifiedError,
    DwgInspection,
    DwgQualificationConfig,
    DwgTargetVersion,
    export_qualified_dwg,
    qualify_backend,
)

from .helpers import FakeDwgBackend, scene


def test_qualification_report_is_deterministic() -> None:
    drawing = scene()
    backend = FakeDwgBackend(drawing)
    first = qualify_backend(drawing, backend)
    second = qualify_backend(drawing, backend)
    assert first.qualified is True
    assert first.report_hash == second.report_hash
    assert first.output_sha256 == second.output_sha256


def test_test_backend_can_exercise_harness_but_never_qualifies_for_production() -> None:
    drawing = scene()
    report = qualify_backend(drawing, FakeDwgBackend(drawing, test_backend=True))
    assert report.qualified is False
    assert "TEST_BACKEND_NOT_PRODUCTION" in report.failures


def test_non_production_backend_fails_closed() -> None:
    drawing = scene()
    report = qualify_backend(drawing, FakeDwgBackend(drawing, production_eligible=False))
    assert report.qualified is False
    assert "BACKEND_NOT_PRODUCTION_ELIGIBLE" in report.failures


def test_semantic_mismatch_fails_qualification() -> None:
    drawing = scene()
    backend = FakeDwgBackend(drawing)
    original = backend.inspect

    def bad_inspection(data: bytes) -> DwgInspection:
        value = original(data)
        return value.model_copy(
            update={
                "fingerprint": value.fingerprint.model_copy(
                    update={"room_count": value.fingerprint.room_count + 1}
                )
            }
        )

    backend.inspect = bad_inspection  # type: ignore[method-assign]
    report = qualify_backend(drawing, backend)
    assert report.qualified is False
    assert "ROOM_COUNT_MISMATCH" in report.failures


def test_scene_hash_loss_fails_qualification() -> None:
    drawing = scene()
    backend = FakeDwgBackend(drawing)
    original = backend.inspect

    def bad_inspection(data: bytes) -> DwgInspection:
        return original(data).model_copy(update={"scene_hash": None})

    backend.inspect = bad_inspection  # type: ignore[method-assign]
    report = qualify_backend(drawing, backend)
    assert report.qualified is False
    assert "SCENE_HASH_MISMATCH" in report.failures


def test_unqualified_report_cannot_export_dwg() -> None:
    drawing = scene()
    backend = FakeDwgBackend(drawing, production_eligible=False)
    report = qualify_backend(drawing, backend)
    with pytest.raises(DwgBackendNotQualifiedError):
        export_qualified_dwg(drawing, backend, report)


def test_qualified_report_is_bound_to_backend_version() -> None:
    drawing = scene()
    backend = FakeDwgBackend(drawing)
    report = qualify_backend(drawing, backend)
    changed = backend.capabilities.model_copy(update={"backend_version": "2.0.0"})
    backend._capabilities = changed  # type: ignore[attr-defined]
    with pytest.raises(DwgBackendNotQualifiedError):
        export_qualified_dwg(drawing, backend, report)


def test_target_is_explicitly_r2018() -> None:
    config = DwgQualificationConfig(target_version=DwgTargetVersion.R2018)
    assert config.target_version is DwgTargetVersion.R2018
