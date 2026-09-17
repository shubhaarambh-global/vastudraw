from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from .models import ConfirmedRequirements, RequirementDraft


class RequirementsStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_environment(cls) -> RequirementsStore:
        app_env = os.getenv("APP_ENV", "development").strip().lower()
        configured = os.getenv("AI_VASTU_REQUIREMENTS_PATH", "").strip()

        if app_env in {"production", "staging"}:
            if not configured:
                raise RuntimeError("AI_VASTU_REQUIREMENTS_PATH is required in production/staging.")
            root = Path(configured)
            if not root.is_absolute():
                raise RuntimeError(
                    "AI_VASTU_REQUIREMENTS_PATH must be an absolute persistent path."
                )
            return cls(root)

        return cls(Path(configured or ".local/requirement-drafts"))

    def _draft_path(self, draft_id: UUID) -> Path:
        return self._root / f"{draft_id}.draft.json"

    def _confirmed_path(self, draft_id: UUID) -> Path:
        return self._root / f"{draft_id}.confirmed.json"

    def save_draft(self, draft: RequirementDraft) -> None:
        path = self._draft_path(draft.draft_id)
        path.write_text(
            draft.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_draft(self, draft_id: UUID) -> RequirementDraft:
        path = self._draft_path(draft_id)
        if not path.exists():
            raise KeyError(str(draft_id))
        return RequirementDraft.model_validate_json(path.read_text(encoding="utf-8"))

    def save_confirmed(self, confirmed: ConfirmedRequirements) -> None:
        draft = self.get_draft(confirmed.draft_id)
        if draft.user_id != confirmed.user_id or draft.project_id != confirmed.project_id:
            raise PermissionError("Confirmed requirements identity mismatch.")
        self._confirmed_path(confirmed.draft_id).write_text(
            confirmed.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_confirmed(self, draft_id: UUID) -> ConfirmedRequirements:
        path = self._confirmed_path(draft_id)
        if not path.exists():
            raise KeyError(str(draft_id))
        return ConfirmedRequirements.model_validate_json(path.read_text(encoding="utf-8"))
