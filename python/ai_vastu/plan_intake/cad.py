from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from ai_vastu.exporting.dxf_importer import DxfImportError, summarize_dxf_bytes

from .errors import PlanIntakeConfigurationError, PlanIntakeProviderError


def summarize_dxf(
    dxf_bytes: bytes,
) -> str:
    try:
        return summarize_dxf_bytes(dxf_bytes)
    except DxfImportError as exc:
        raise PlanIntakeProviderError(str(exc)) from exc


def convert_dwg_to_dxf(dwg_bytes: bytes) -> bytes:
    executable = os.getenv("AI_VASTU_DWG_IMPORT_EXECUTABLE", "").strip()
    args_json = os.getenv("AI_VASTU_DWG_IMPORT_ARGS_JSON", "").strip()

    if not executable or not args_json:
        raise PlanIntakeConfigurationError(
            "DWG analysis requires AI_VASTU_DWG_IMPORT_EXECUTABLE and "
            "AI_VASTU_DWG_IMPORT_ARGS_JSON. Upload DXF/PDF instead when a "
            "DWG-to-DXF backend is not configured."
        )

    try:
        raw_args = json.loads(args_json)
    except json.JSONDecodeError as exc:
        raise PlanIntakeConfigurationError(
            "AI_VASTU_DWG_IMPORT_ARGS_JSON must be a JSON array of argv strings."
        ) from exc

    if not isinstance(raw_args, list) or not all(isinstance(item, str) for item in raw_args):
        raise PlanIntakeConfigurationError(
            "AI_VASTU_DWG_IMPORT_ARGS_JSON must be a JSON array of argv strings."
        )

    joined = " ".join(raw_args)
    if "{input_dwg}" not in joined or "{output_dxf}" not in joined:
        raise PlanIntakeConfigurationError(
            "DWG import args must contain {input_dwg} and {output_dxf} placeholders."
        )

    with tempfile.TemporaryDirectory(prefix="ai-vastu-dwg-") as temp_dir:
        input_path = Path(temp_dir) / "input.dwg"
        output_path = Path(temp_dir) / "output.dxf"
        input_path.write_bytes(dwg_bytes)

        args = [
            item.replace("{input_dwg}", str(input_path)).replace("{output_dxf}", str(output_path))
            for item in raw_args
        ]

        try:
            completed = subprocess.run(
                [executable, *args],
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PlanIntakeProviderError(f"DWG-to-DXF converter could not execute: {exc}") from exc

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:1000]
            raise PlanIntakeProviderError(
                f"DWG-to-DXF converter failed with exit code {completed.returncode}: {detail}"
            )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise PlanIntakeProviderError("DWG-to-DXF converter did not produce a DXF file.")
        return output_path.read_bytes()
