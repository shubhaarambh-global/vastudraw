from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4


@contextmanager
def workspace_temporary_directory(prefix: str) -> Iterator[Path]:
    configured_root = os.environ.get("AI_VASTU_PROCESS_TMP_ROOT", "").strip()
    if not configured_root:
        raise RuntimeError("AI_VASTU_PROCESS_TMP_ROOT is required by the project Python runner.")

    root = Path(configured_root)
    root.mkdir(parents=True, exist_ok=True)
    directory = root / f"{prefix}-{uuid4().hex}"
    directory.mkdir()
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)
