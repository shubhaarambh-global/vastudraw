from __future__ import annotations

from ai_vastu.dwg import (
    DwgBackendCapabilities,
    DwgBackendKind,
    DwgInspection,
    DwgTargetVersion,
    expected_fingerprint,
)
from ai_vastu.exporting import DrawingScene, build_drawing_scene
from tests.exporting.helpers import export_plan


class FakeDwgBackend:
    def __init__(
        self,
        scene: DrawingScene,
        *,
        production_eligible: bool = True,
        test_backend: bool = False,
    ) -> None:
        assert scene.scene_hash is not None
        self._scene = scene
        self._production_eligible = production_eligible
        self._test_backend = test_backend
        self._capabilities = DwgBackendCapabilities(
            backend_id="fake-qualified-backend",
            kind=DwgBackendKind.EXTERNAL_COMMAND,
            backend_version="1.0.0",
            supported_targets=(DwgTargetVersion.R2018,),
            modern_dwg_write=True,
            roundtrip_inspection=True,
            production_eligible=production_eligible,
            test_backend=test_backend,
        )

    @property
    def capabilities(self) -> DwgBackendCapabilities:
        return self._capabilities

    def convert_dxf(self, dxf_bytes: bytes, target_version: DwgTargetVersion) -> bytes:
        assert dxf_bytes
        assert target_version is DwgTargetVersion.R2018
        return b"AC1032" + self._scene.scene_hash.encode("ascii") + b"\x00FAKE"

    def inspect(self, dwg_bytes: bytes) -> DwgInspection:
        assert dwg_bytes.startswith(b"AC1032")
        return DwgInspection(
            dwg_version_code="AC1032",
            units="MM",
            layers=(
                "AIA_PLOT",
                "AIA_BUILDABLE",
                "AIA_FLOOR",
                "AIA_ROOM",
                "AIA_WALL_EXT",
                "AIA_WALL_INT",
                "AIA_OPENING",
                "AIA_DIM",
                "AIA_ANNOT",
                "AIA_NORTH",
            ),
            scene_hash=self._scene.scene_hash,
            fingerprint=expected_fingerprint(self._scene),
        )


def scene() -> DrawingScene:
    result = build_drawing_scene(export_plan())
    assert result.scene_hash is not None
    return result
