from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

from project_smoke_fixture import sample_plan

from ai_vastu.projects import (
    AppendRevisionCommand,
    PostgresProjectRepository,
    ProjectRevisionService,
)


def _plan(project_id, revision_id):
    return (
        sample_plan(revision_id)
        .model_copy(
            update={
                "project_id": project_id,
                "revision_id": revision_id,
                "content_hash": None,
            }
        )
        .with_content_hash()
    )


def main() -> None:
    database_url = os.environ.get("AI_VASTU_TEST_POSTGRES_DSN", "").strip()
    if not database_url:
        raise SystemExit("AI_VASTU_TEST_POSTGRES_DSN is required for the live smoke test.")

    project_id = uuid4()
    revision_1 = uuid4()
    revision_2 = uuid4()
    fixed_time = datetime(2026, 9, 15, tzinfo=UTC)

    repository = PostgresProjectRepository(database_url)
    try:
        service = ProjectRevisionService(repository, clock=lambda: fixed_time)
        service.create_project("Phase 18 PostgreSQL Smoke", project_id)
        first = service.append_revision(
            AppendRevisionCommand(
                project_id=project_id,
                document=_plan(project_id, revision_1),
            )
        )
        second = service.append_revision(
            AppendRevisionCommand(
                project_id=project_id,
                document=_plan(project_id, revision_2),
                expected_parent_revision_id=revision_1,
            )
        )
        loaded = service.get_project(project_id)
        revisions = service.list_revisions(project_id)
    finally:
        repository.close()

    if loaded.current_revision_id != revision_2 or loaded.current_revision_number != 2:
        raise SystemExit("PostgreSQL project head did not advance atomically.")
    if tuple(item.revision_id for item in revisions) != (revision_1, revision_2):
        raise SystemExit("PostgreSQL revision ordering or reload failed.")
    if first.parent_revision_id is not None or second.parent_revision_id != revision_1:
        raise SystemExit("PostgreSQL revision ancestry is incorrect.")

    print(
        "PostgreSQL live persistence smoke passed: "
        f"project={project_id}, revisions=2, current=2, payload_hash={second.payload_hash}"
    )


if __name__ == "__main__":
    main()
