from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    """Use an accessible per-test directory on managed Windows hosts."""

    configured = os.environ.get("AI_VASTU_PYTEST_TMP_ROOT", "").strip()
    if not configured:
        raise RuntimeError("AI_VASTU_PYTEST_TMP_ROOT is required by this pytest profile.")
    root = Path(configured)
    root.mkdir(parents=True, exist_ok=True)
    path = root / uuid4().hex
    path.mkdir(exist_ok=False)
    return path.resolve()
