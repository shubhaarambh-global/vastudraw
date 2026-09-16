from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .errors import DwgBackendExecutionError, DwgInspectionError
from .models import (
    DwgBackendCapabilities,
    DwgBackendKind,
    DwgInspection,
    DwgTargetVersion,
    ExternalCommandBackendConfig,
)


class ExternalCommandDwgBackend:
    """Adapter for a separately installed/licensed DWG converter + inspector.

    Commands are argv arrays and always execute with shell=False. The repository does not
    bundle an ODA or LibreDWG binary and never silently falls back to renaming DXF bytes.
    """

    def __init__(
        self,
        config: ExternalCommandBackendConfig,
        *,
        production_eligible: bool,
        kind: DwgBackendKind = DwgBackendKind.EXTERNAL_COMMAND,
    ) -> None:
        self._config = config
        self._capabilities = DwgBackendCapabilities(
            backend_id=config.backend_id,
            kind=kind,
            backend_version=config.backend_version,
            supported_targets=(config.target_version,),
            modern_dwg_write=True,
            roundtrip_inspection=True,
            production_eligible=production_eligible,
        )

    @property
    def capabilities(self) -> DwgBackendCapabilities:
        return self._capabilities

    def _run(self, executable: str, args: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [executable, *args],
                check=True,
                capture_output=True,
                text=True,
                shell=False,
                timeout=self._config.timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise DwgBackendExecutionError(f"DWG backend command failed: {executable}") from exc

    @staticmethod
    def _format_args(args: tuple[str, ...], values: dict[str, str]) -> tuple[str, ...]:
        return tuple(item.format_map(values) for item in args)

    def convert_dxf(self, dxf_bytes: bytes, target_version: DwgTargetVersion) -> bytes:
        if target_version != self._config.target_version:
            raise DwgBackendExecutionError(
                "Requested target version is not configured for this backend."
            )
        with tempfile.TemporaryDirectory(prefix="ai-vastu-dwg-") as directory:
            root = Path(directory)
            input_dxf = root / "input.dxf"
            output_dwg = root / "output.dwg"
            input_dxf.write_bytes(dxf_bytes)
            values = {
                "input_dxf": str(input_dxf),
                "output_dwg": str(output_dwg),
                "version": target_version.value,
            }
            args = self._format_args(self._config.converter_args, values)
            self._run(self._config.converter_executable, args)
            if not output_dwg.is_file():
                raise DwgBackendExecutionError(
                    "DWG converter did not create the requested output file."
                )
            return output_dwg.read_bytes()

    def inspect(self, dwg_bytes: bytes) -> DwgInspection:
        with tempfile.TemporaryDirectory(prefix="ai-vastu-dwg-inspect-") as directory:
            input_dwg = Path(directory) / "input.dwg"
            input_dwg.write_bytes(dwg_bytes)
            values = {"input_dwg": str(input_dwg), "version": self._config.target_version.value}
            args = self._format_args(self._config.inspector_args, values)
            completed = self._run(self._config.inspector_executable, args)
            try:
                payload: Any = json.loads(completed.stdout)
                return DwgInspection.model_validate(payload)
            except (json.JSONDecodeError, ValueError) as exc:
                raise DwgInspectionError(
                    "DWG inspector did not emit a valid inspection document."
                ) from exc
