from __future__ import annotations

import os
from pathlib import Path

from .models import SoftVastuCatalog


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def catalog_path() -> Path:
    configured = os.getenv("AI_VASTU_SOFT_VASTU_CATALOG_PATH", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            raise ValueError("AI_VASTU_SOFT_VASTU_CATALOG_PATH must be absolute.")
        return path
    return repository_root() / "docs" / "vastu" / "spec-v2-draft" / "seed-rule-catalog.json"


def load_soft_vastu_catalog() -> SoftVastuCatalog:
    path = catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"Soft Vastu catalog not found: {path}")
    return SoftVastuCatalog.model_validate_json(path.read_text(encoding="utf-8"))
