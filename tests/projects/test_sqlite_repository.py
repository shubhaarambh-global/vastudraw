from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from tests.plan_schema.sample import PROJECT_ID, sample_plan

from ai_vastu.projects import (
    AppendRevisionCommand,
    DuplicateRevisionError,
    ProjectRevisionService,
    RevisionConflictError,
    SqliteProjectRepository,
)

REVISION_1 = UUID("22222222-2222-2222-2222-222222222221")
REVISION_2 = UUID("22222222-2222-2222-2222-222222222222")
REVISION_3 = UUID("22222222-2222-2222-2222-222222222223")
FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _plan(revision_id: UUID):
    return sample_plan().model_copy(update={"revision_id": revision_id}).with_content_hash()


def _service(path: Path) -> tuple[ProjectRevisionService, SqliteProjectRepository]:
    repository = SqliteProjectRepository(path)
    return ProjectRevisionService(repository, clock=lambda: FIXED_TIME), repository


def test_revisions_persist_across_repository_reopen(tmp_path: Path) -> None:
    database_path = tmp_path / "projects.sqlite3"
    service, repository = _service(database_path)
    service.create_project("House A", PROJECT_ID)
    first = service.append_revision(
        AppendRevisionCommand(project_id=PROJECT_ID, document=_plan(REVISION_1))
    )
    second = service.append_revision(
        AppendRevisionCommand(
            project_id=PROJECT_ID,
            document=_plan(REVISION_2),
            expected_parent_revision_id=REVISION_1,
        )
    )
    repository.close()

    reopened = SqliteProjectRepository(database_path)
    project = reopened.get_project(PROJECT_ID)
    revisions = reopened.list_revisions(PROJECT_ID)
    reopened.close()

    assert project.current_revision_id == REVISION_2
    assert project.current_revision_number == 2
    assert tuple(item.revision_id for item in revisions) == (REVISION_1, REVISION_2)
    assert first.plan_document_hash == first.document.content_hash
    assert second.parent_revision_id == REVISION_1


def test_append_requires_current_parent(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "projects.sqlite3")
    service.create_project("House A", PROJECT_ID)
    service.append_revision(
        AppendRevisionCommand(project_id=PROJECT_ID, document=_plan(REVISION_1))
    )

    with pytest.raises(RevisionConflictError):
        service.append_revision(
            AppendRevisionCommand(
                project_id=PROJECT_ID,
                document=_plan(REVISION_2),
                expected_parent_revision_id=None,
            )
        )
    repository.close()


def test_revision_ids_are_immutable_and_unique(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "projects.sqlite3")
    service.create_project("House A", PROJECT_ID)
    service.append_revision(
        AppendRevisionCommand(project_id=PROJECT_ID, document=_plan(REVISION_1))
    )

    with pytest.raises(DuplicateRevisionError):
        service.append_revision(
            AppendRevisionCommand(
                project_id=PROJECT_ID,
                document=_plan(REVISION_1),
                expected_parent_revision_id=REVISION_1,
            )
        )
    repository.close()


def test_payload_hash_excludes_created_at_but_covers_revision_payload(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "projects.sqlite3")
    service.create_project("House A", PROJECT_ID)
    first = service.append_revision(
        AppendRevisionCommand(project_id=PROJECT_ID, document=_plan(REVISION_1), note="baseline")
    )
    repository.close()

    changed = first.model_copy(update={"note": "changed"})
    assert changed.compute_payload_hash() != first.payload_hash


def test_project_ownership_is_persisted_and_filterable(tmp_path: Path) -> None:
    service, repository = _service(tmp_path / "projects.sqlite3")
    owner_a = UUID("aaaaaaaa-1919-1919-1919-191919191919")
    owner_b = UUID("bbbbbbbb-1919-1919-1919-191919191919")
    service.create_project("House A", PROJECT_ID, owner_a)

    assert service.is_project_owner(PROJECT_ID, owner_a)
    assert not service.is_project_owner(PROJECT_ID, owner_b)
    assert tuple(item.project_id for item in service.list_projects_for_owner(owner_a)) == (
        PROJECT_ID,
    )
    assert service.list_projects_for_owner(owner_b) == ()
    repository.close()
