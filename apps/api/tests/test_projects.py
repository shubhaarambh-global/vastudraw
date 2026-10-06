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


def test_confirmed_geometry_save_checks_access_after_parent_conflict(monkeypatch) -> None:
    from tests.validation.test_revision_access import document

    import ai_vastu.validation.revision_access as access

    repository = SqliteProjectRepository(":memory:")
    client = TestClient(create_app(repository, DevelopmentAccessTokenVerifier(TOKEN, USER_ID)))
    client.post("/projects", json={"name": "Access fixture", "project_id": str(PROJECT_ID)},
                headers=AUTH)
    prior = document().model_copy(update={"revision_id": REVISION_1}).with_content_hash()
    first = client.post(f"/projects/{PROJECT_ID}/revisions",
                        json={"document": prior.model_dump(mode="json")}, headers=AUTH)
    assert first.status_code == 201
    changed_floor = prior.floors[0].model_copy(update={"openings": ()})
    changed = prior.model_copy(update={"revision_id": REVISION_2,
        "floors": (changed_floor,), "content_hash": None}).with_content_hash()
    payload = {"document": changed.model_dump(mode="json"),
               "expected_parent_revision_id": str(REVISION_1)}
    rejected = client.post(f"/projects/{PROJECT_ID}/revisions", json=payload, headers=AUTH)
    assert rejected.status_code == 422
    assert len(client.get(f"/projects/{PROJECT_ID}/revisions", headers=AUTH).json()) == 1

    def forbidden(**kwargs):
        raise AssertionError("Stale parent must fail before access validation")

    monkeypatch.setattr(access, "validate_changed_revision_access", forbidden)
    stale = client.post(f"/projects/{PROJECT_ID}/revisions",
                        json={"document": changed.model_dump(mode="json")}, headers=AUTH)
    assert stale.status_code == 409
    repository.close()
