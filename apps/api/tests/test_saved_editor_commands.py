import json
from typing import cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from apps.api.tests.test_revision_chat import canonical_context as canonical_context
from apps.api.tests.test_revision_chat import context as context
from fastapi.testclient import TestClient
from httpx import Response

from ai_vastu.plan_schema import PlanDocument

Context = tuple[TestClient, Mock, dict[str, str], str, str]


def _edit(
    client: TestClient, auth: dict[str, str], project: str, base: str, room: str, target: int
) -> Response:
    return cast(
        Response,
        client.post(
            f"/projects/{project}/editor-commands",
            headers=auth,
            json={
                "protocol_version": "1.0.0",
                "project_id": project,
                "base_revision_id": base,
                "commands": [
                    {
                        "kind": "ROOM_SET_DIMENSION",
                        "room_id": room,
                        "axis": "WIDTH",
                        "target_mm": target,
                    }
                ],
            },
        ),
    )


def test_manual_dimension_is_exact_preserves_clear_minimum_and_ancestry(context: Context) -> None:
    client, interpreter, auth, project, base = context
    original = client.get(f"/projects/{project}/revisions/{base}", headers=auth).json()
    document = original["document"]
    room = next(r for f in document["floors"] for r in f["rooms"] if r["room_type"] == "kitchen")
    xs = [p["x_mm"] for p in room["polygon"]["outer"]]
    target = max(xs) - min(xs) + 100
    response = _edit(client, auth, project, base, room["id"], target)
    assert response.status_code == 200, response.text
    revision = response.json()["revision"]
    changed = revision["document"]
    revised_room = next(
        r
        for f in changed["floors"]
        for r in f["rooms"]
        if r["requirement_id"] == room["requirement_id"]
    )
    revised_xs = [p["x_mm"] for p in revised_room["polygon"]["outer"]]
    assert max(revised_xs) - min(revised_xs) == target
    before_req = next(r for r in document["room_requirements"] if r["id"] == room["requirement_id"])
    after_req = next(r for r in changed["room_requirements"] if r["id"] == room["requirement_id"])
    assert after_req["min_width_mm"] >= before_req["min_width_mm"]
    assert after_req["max_width_mm"] == target
    assert changed["validation"]["valid"] is True
    assert revision["parent_revision_id"] == base
    assert client.get(f"/projects/{project}/revisions/{base}", headers=auth).json() == original
    interpreter.assert_not_called()


@pytest.mark.parametrize("violation", ["off_grid", "clear_minimum", "existing_maximum"])
def test_manual_dimension_bounds_fail_closed_without_rounding_or_append(
    context: Context,
    violation: str,
) -> None:
    client, interpreter, auth, project, base = context
    original = client.get(f"/projects/{project}/revisions/{base}", headers=auth).json()
    document = PlanDocument.model_validate_json(json.dumps(original["document"]))
    room = next(r for f in document.floors for r in f.rooms if r.room_type.value == "kitchen")
    xs = [p.x_mm for p in room.polygon.outer]
    width = max(xs) - min(xs)
    requirement = next(r for r in document.room_requirements if r.id == room.requirement_id)
    target = width + 101
    if violation == "clear_minimum":
        target = requirement.min_width_mm + 230 - 10
    elif violation == "existing_maximum":
        document = document.model_copy(
            update={
                "revision_id": uuid4(),
                "content_hash": None,
                "room_requirements": tuple(
                    r.model_copy(update={"max_width_mm": width + 90})
                    if r.id == room.requirement_id
                    else r
                    for r in document.room_requirements
                ),
            }
        ).with_content_hash()
        saved = client.post(
            f"/projects/{project}/revisions",
            headers=auth,
            json={
                "document": document.model_dump(mode="json"),
                "expected_parent_revision_id": base,
            },
        )
        assert saved.status_code == 201
        base = saved.json()["revision_id"]
        target = width + 100
    history = client.get(f"/projects/{project}/revisions", headers=auth).json()
    response = _edit(client, auth, project, base, str(room.id), target)
    assert response.status_code == 422
    assert client.get(f"/projects/{project}/revisions", headers=auth).json() == history
    interpreter.assert_not_called()
