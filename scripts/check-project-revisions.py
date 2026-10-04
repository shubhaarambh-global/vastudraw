from datetime import UTC, datetime

from project_smoke_fixture import PROJECT_ID, REVISION_1, REVISION_2, sample_plan
from workspace_temp import workspace_temporary_directory

from ai_vastu.projects import AppendRevisionCommand, ProjectRevisionService, SqliteProjectRepository

FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


with workspace_temporary_directory("projects-check") as temporary_directory:
    database_path = temporary_directory / "projects.sqlite3"
    repository = SqliteProjectRepository(database_path)
    service = ProjectRevisionService(repository, clock=lambda: FIXED_TIME)
    project = service.create_project("Smoke Project", PROJECT_ID)
    first = service.append_revision(
        AppendRevisionCommand(project_id=PROJECT_ID, document=sample_plan(REVISION_1))
    )
    second = service.append_revision(
        AppendRevisionCommand(
            project_id=PROJECT_ID,
            document=sample_plan(REVISION_2),
            expected_parent_revision_id=REVISION_1,
        )
    )
    repository.close()

    reopened = SqliteProjectRepository(database_path)
    revisions = reopened.list_revisions(PROJECT_ID)
    loaded_project = reopened.get_project(PROJECT_ID)
    reopened.close()

if project.current_revision_number != 0:
    raise SystemExit("Fresh project unexpectedly has revisions.")
if tuple(item.revision_id for item in revisions) != (REVISION_1, REVISION_2):
    raise SystemExit("Revision ordering or durable reload failed.")
if loaded_project.current_revision_id != REVISION_2 or loaded_project.current_revision_number != 2:
    raise SystemExit("Current revision pointer was not persisted atomically.")
if first.parent_revision_id is not None or second.parent_revision_id != REVISION_1:
    raise SystemExit("Revision ancestry is incorrect.")
print(
    "Project revisions deterministic: "
    f"project={PROJECT_ID}, revisions={len(revisions)}, "
    f"current={loaded_project.current_revision_number}, "
    f"payload_hash={second.payload_hash}"
)
