from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from .models import AppendRevisionCommand, ProjectRecord, RevisionRecord


class ProjectRepository(Protocol):
    def close(self) -> None: ...

    def create_project(
        self,
        project_id: UUID,
        name: str,
        created_at: datetime,
        owner_user_id: UUID | None = None,
    ) -> ProjectRecord: ...

    def get_project(self, project_id: UUID) -> ProjectRecord: ...

    def list_projects_for_owner(self, owner_user_id: UUID) -> tuple[ProjectRecord, ...]: ...

    def is_project_owner(self, project_id: UUID, owner_user_id: UUID) -> bool: ...

    def append_revision(
        self,
        command: AppendRevisionCommand,
        created_at: datetime,
    ) -> RevisionRecord: ...

    def get_revision(self, project_id: UUID, revision_id: UUID) -> RevisionRecord: ...

    def list_revisions(self, project_id: UUID) -> tuple[RevisionRecord, ...]: ...
