from __future__ import annotations

import json
from uuid import UUID

from fastapi.testclient import TestClient
from tests.plan_schema.sample import PROJECT_ID, sample_plan

from ai_vastu.auth import DevelopmentAccessTokenVerifier
from ai_vastu.projects import SqliteProjectRepository
from app.main import create_app

REVISION_1 = UUID("22222222-2222-2222-2222-222222222221")
REVISION_2 = UUID("22222222-2222-2222-2222-222222222222")
USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TOKEN = "project-test-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _payload(revision_id: UUID) -> dict[str, object]:
    plan = sample_plan().model_copy(update={"revision_id": revision_id}).with_content_hash()
    return json.loads(plan.to_canonical_json())


def test_project_revision_api_is_append_only_and_loadable() -> None:
    repository = SqliteProjectRepository(":memory:")
    client = TestClient(create_app(repository, DevelopmentAccessTokenVerifier(TOKEN, USER_ID)))

    created = client.post(
        "/projects",
        json={"name": "House A", "project_id": str(PROJECT_ID)},
        headers=AUTH,
    )
    assert created.status_code == 201
    assert created.json()["current_revision_number"] == 0

    first = client.post(
        f"/projects/{PROJECT_ID}/revisions",
        json={"document": _payload(REVISION_1)},
        headers=AUTH,
    )
    assert first.status_code == 201
    assert first.json()["revision_number"] == 1

    stale = client.post(
        f"/projects/{PROJECT_ID}/revisions",
        json={"document": _payload(REVISION_2)},
        headers=AUTH,
    )
    assert stale.status_code == 409

    second = client.post(
        f"/projects/{PROJECT_ID}/revisions",
        json={
            "document": _payload(REVISION_2),
            "expected_parent_revision_id": str(REVISION_1),
        },
        headers=AUTH,
    )
    assert second.status_code == 201
    assert second.json()["revision_number"] == 2

    listed = client.get(f"/projects/{PROJECT_ID}/revisions", headers=AUTH)
    assert listed.status_code == 200
    assert [item["revision_id"] for item in listed.json()] == [
        str(REVISION_1),
        str(REVISION_2),
    ]
    repository.close()
