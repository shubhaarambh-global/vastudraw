from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import DwgBackendCapabilities, DwgInspection, DwgTargetVersion


@runtime_checkable
class DwgBackend(Protocol):
    @property
    def capabilities(self) -> DwgBackendCapabilities: ...

    def convert_dxf(self, dxf_bytes: bytes, target_version: DwgTargetVersion) -> bytes: ...

    def inspect(self, dwg_bytes: bytes) -> DwgInspection: ...
