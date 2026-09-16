from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .models import AppendRevisionCommand, ProjectRecord, RevisionRecord
from .repository import ProjectRepository

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectRevisionService:
    def __init__(self, repository: ProjectRepository, clock: Clock = _utc_now) -> None:
        self._repository = repository
        self._clock = clock

    def create_project(
        self,
        name: str,
        project_id: UUID | None = None,
        owner_user_id: UUID | None = None,
    ) -> ProjectRecord:
        return self._repository.create_project(
            project_id or uuid4(),
            name,
            self._clock(),
            owner_user_id,
        )

    def get_project(self, project_id: UUID) -> ProjectRecord:
        return self._repository.get_project(project_id)

    def list_projects_for_owner(self, owner_user_id: UUID) -> tuple[ProjectRecord, ...]:
        return self._repository.list_projects_for_owner(owner_user_id)

    def is_project_owner(self, project_id: UUID, owner_user_id: UUID) -> bool:
        return self._repository.is_project_owner(project_id, owner_user_id)

    def append_revision(self, command: AppendRevisionCommand) -> RevisionRecord:
        return self._repository.append_revision(command, self._clock())

    def get_revision(self, project_id: UUID, revision_id: UUID) -> RevisionRecord:
        return self._repository.get_revision(project_id, revision_id)

    def list_revisions(self, project_id: UUID) -> tuple[RevisionRecord, ...]:
        return self._repository.list_revisions(project_id)
