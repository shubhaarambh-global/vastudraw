from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID

from ai_vastu.projects import PostgresProjectRepository


def main() -> None:
    dsn = os.environ.get("AI_VASTU_TEST_POSTGRES_DSN", "").strip()
    if not dsn:
        raise SystemExit("AI_VASTU_TEST_POSTGRES_DSN is required for auth:live.")

    owner_a = UUID("19191919-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    owner_b = UUID("19191919-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    project_a = UUID("19191919-0000-0000-0000-000000000001")
    project_b = UUID("19191919-0000-0000-0000-000000000002")
    created_at = datetime(2026, 9, 15, tzinfo=UTC)

    repository = PostgresProjectRepository(dsn, min_pool_size=1, max_pool_size=2)
    try:
        repository.create_project(project_a, "Owner A project", created_at, owner_a)
        repository.create_project(project_b, "Owner B project", created_at, owner_b)

        assert repository.is_project_owner(project_a, owner_a)
        assert not repository.is_project_owner(project_a, owner_b)
        assert tuple(
            project.project_id for project in repository.list_projects_for_owner(owner_a)
        ) == (project_a,)
        assert tuple(
            project.project_id for project in repository.list_projects_for_owner(owner_b)
        ) == (project_b,)
    finally:
        repository.close()

    print("PostgreSQL project-ownership live smoke passed: owners=2, isolated=true")


if __name__ == "__main__":
    main()
