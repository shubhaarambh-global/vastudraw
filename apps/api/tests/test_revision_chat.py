import json
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_vastu.architectural_brain.models import (
    RevisionDirective,
    RevisionOperation,
    StructuredRevisionIntent,
)
from ai_vastu.auth import DevelopmentAccessTokenVerifier
from ai_vastu.plan_schema import PlanDocument
from ai_vastu.projects import AppendRevisionCommand, ProjectRevisionService, SqliteProjectRepository
from ai_vastu.provider_runtime import ProviderFailureCategory, ProviderRuntimeError
from ai_vastu.requirements.finalization import CanonicalGeneration, build_canonical_plan_document
from ai_vastu.requirements.generation_adapter import (
    compile_confirmed_requirements,
    run_compiled_generation,
)
from ai_vastu.requirements.models import ConfirmedRequirements, ConfirmedRoomRequirement, Direction
from ai_vastu.requirements.store import RequirementsStore
from app import revision_chat_routes
from app.main import create_app


@pytest.fixture(scope="module")
def canonical_context() -> tuple[ConfirmedRequirements, CanonicalGeneration]:
    user_id, project_id = uuid4(), uuid4()
    confirmed = ConfirmedRequirements(
        draft_id=uuid4(),
        user_id=user_id,
        project_id=project_id,
        user_confirmed=True,
        plot_width_mm=9144,
        plot_depth_mm=15240,
        north_rotation_deg=0,
        road_side=Direction.E,
        floor_count=1,
        bedroom_count=1,
        parking_count=0,
        rooms=[
            ConfirmedRoomRequirement(room_type=kind, quantity=1)
            for kind in ("bedroom", "dining", "kitchen")
        ],
    )
    compiled = compile_confirmed_requirements(confirmed)
    compiled = replace(
        compiled,
        request=compiled.request.model_copy(
            update={
                "room_requirements": tuple(
                    r.model_copy(update={"preferred_width_mm": r.min_width_mm})
                    for r in compiled.request.room_requirements
                ),
            }
        ),
    )
    canonical = build_canonical_plan_document(
        confirmed=confirmed,
        compiled=compiled,
        result=run_compiled_generation(compiled),
    )
    return confirmed, canonical


@pytest.fixture
def context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    canonical_context: tuple[ConfirmedRequirements, CanonicalGeneration],
) -> Iterator[tuple[TestClient, Mock, dict[str, str], str, str]]:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AI_VASTU_REVISION_PROVIDER", "ollama_local")
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PATH", str(tmp_path))
    confirmed, canonical = canonical_context
    user_id, project_id = confirmed.user_id, confirmed.project_id
    repository = SqliteProjectRepository(":memory:")
    service = ProjectRevisionService(repository)
    service.create_project("Revision fixture", project_id, user_id)
    base = service.append_revision(
        AppendRevisionCommand(project_id=project_id, document=canonical.document)
    )
    monkeypatch.setattr(
        RequirementsStore, "confirmed_for_context", lambda self, **kwargs: confirmed
    )
    interpreter = Mock(
        return_value=StructuredRevisionIntent(
            project_id=project_id,
            base_revision_id=base.revision_id,
            original_request="private request",
            directives=(
                RevisionDirective(
                    operation=RevisionOperation.INCREASE_DIMENSION,
                    room_type="kitchen",
                    axis="WIDTH",
                    delta_mm=305,
                ),
            ),
        )
    )
    monkeypatch.setattr(revision_chat_routes, "interpret_revision_with_ollama_local", interpreter)
    client = TestClient(
        create_app(repository, DevelopmentAccessTokenVerifier("revision-token", user_id))
    )
    yield (
        client,
        interpreter,
        {"Authorization": "Bearer revision-token"},
        str(project_id),
        str(base.revision_id),
    )
    repository.close()


@pytest.mark.parametrize("delta_mm", [100, 305])
def test_revision_chat_regenerates_and_preserves_immutable_ancestry(
    context: tuple[TestClient, Mock, dict[str, str], str, str],
    delta_mm: int,
) -> None:
    client, interpreter, auth, project, base_id = context
    interpreter.return_value = interpreter.return_value.model_copy(
        update={
            "directives": (
                interpreter.return_value.directives[0].model_copy(
                    update={
                        "delta_mm": delta_mm,
                    }
                ),
            ),
        }
    )
    original = client.get(f"/projects/{project}/revisions/{base_id}", headers=auth).json()
    response = client.post(
        f"/projects/{project}/revision-chat",
        headers=auth,
        json={"base_revision_id": base_id, "request": f"make kitchen {delta_mm} mm wider"},
    )
    assert response.status_code == 200, response.text
    revision = response.json()["revision"]
    assert revision["parent_revision_id"] == base_id
    assert revision["revision_number"] == 2
    assert revision["document"]["validation"]["valid"] is True
    before_room = next(
        r for f in original["document"]["floors"] for r in f["rooms"] if r["room_type"] == "kitchen"
    )
    after_room = next(
        r for f in revision["document"]["floors"] for r in f["rooms"] if r["room_type"] == "kitchen"
    )
    before_width = max(p["x_mm"] for p in before_room["polygon"]["outer"]) - min(
        p["x_mm"] for p in before_room["polygon"]["outer"]
    )
    after_width = max(p["x_mm"] for p in after_room["polygon"]["outer"]) - min(
        p["x_mm"] for p in after_room["polygon"]["outer"]
    )
    change = response.json()["dimension_change"]
    step = change["solver_step_mm"]
    requested = before_width + delta_mm
    applied = ((requested + step - 1) // step) * step
    assert after_width == applied
    assert change == {
        "room_type": "kitchen",
        "axis": "WIDTH",
        "previous_mm": before_width,
        "requested_mm": requested,
        "applied_mm": applied,
        "rounding_mm": applied - requested,
        "solver_step_mm": step,
    }
    assert after_width - before_width == (100 if delta_mm == 100 else 310)
    assert revision["document"]["plot"] == original["document"]["plot"]
    assert revision["document"]["roads"] == original["document"]["roads"]
    assert "private request" not in response.text
    assert client.get(f"/projects/{project}/revisions/{base_id}", headers=auth).json() == original
    assert (
        client.get(f"/projects/{project}/revisions/{revision['revision_id']}", headers=auth).json()
        == revision
    )
    interpreter.assert_called_once()

    stale = client.post(
        f"/projects/{project}/revision-chat",
        headers=auth,
        json={"base_revision_id": base_id, "request": "make kitchen 1 ft wider"},
    )
    assert stale.status_code == 409
    interpreter.assert_called_once()


def test_rounded_dimension_exceeding_existing_maximum_is_rejected(
    context: tuple[TestClient, Mock, dict[str, str], str, str],
) -> None:
    client, _, auth, project, base_id = context
    original = client.get(f"/projects/{project}/revisions/{base_id}", headers=auth).json()
    document = PlanDocument.model_validate_json(json.dumps(original["document"]))
    room = next(r for f in document.floors for r in f.rooms if r.room_type.value == "kitchen")
    xs = [p.x_mm for p in room.polygon.outer]
    maximum = max(xs) - min(xs) + 305
    document = document.model_copy(
        update={
            "revision_id": uuid4(),
            "content_hash": None,
            "room_requirements": tuple(
                req.model_copy(update={"max_width_mm": maximum})
                if req.id == room.requirement_id
                else req
                for req in document.room_requirements
            ),
        }
    ).with_content_hash()
    saved = client.post(
        f"/projects/{project}/revisions",
        headers=auth,
        json={
            "document": document.model_dump(mode="json"),
            "expected_parent_revision_id": base_id,
        },
    )
    assert saved.status_code == 201
    base = saved.json()["revision_id"]
    history_before = client.get(f"/projects/{project}/revisions", headers=auth).json()
    response = client.post(
        f"/projects/{project}/revision-chat",
        headers=auth,
        json={
            "base_revision_id": base,
            "request": "increase kitchen width by 305 mm",
        },
    )
    assert response.status_code == 422
    assert client.get(f"/projects/{project}/revisions", headers=auth).json() == history_before


def test_infeasible_exact_revision_preserves_history_without_relaxation(
    context: tuple[TestClient, Mock, dict[str, str], str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, interpreter, auth, project, base = context
    generator = Mock(side_effect=ValueError("Exact target is infeasible."))
    monkeypatch.setattr(revision_chat_routes, "regenerate_room_dimension", generator)
    before = client.get(f"/projects/{project}/revisions", headers=auth).json()
    response = client.post(
        f"/projects/{project}/revision-chat",
        headers=auth,
        json={
            "base_revision_id": base,
            "request": "increase kitchen width by 305 mm",
        },
    )
    assert response.status_code == 422
    interpreter.assert_called_once()
    generator.assert_called_once()
    assert generator.call_args.kwargs["exact"] is True
    assert client.get(f"/projects/{project}/revisions", headers=auth).json() == before


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_revision_chat_denies_hosted_environment_before_ollama(
    context: tuple[TestClient, Mock, dict[str, str], str, str],
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    client, interpreter, auth, project, base = context
    monkeypatch.setenv("APP_ENV", environment)
    response = client.post(
        f"/projects/{project}/revision-chat",
        headers=auth,
        json={"base_revision_id": base, "request": "make kitchen wider"},
    )
    # Production middleware rejects development auth before the route executes.
    assert response.status_code == (503 if environment == "production" else 403)
    interpreter.assert_not_called()


def test_revision_chat_rejects_unsupported_and_provider_failure_without_append(
    context: tuple[TestClient, Mock, dict[str, str], str, str],
) -> None:
    client, interpreter, auth, project, base = context
    interpreter.return_value = interpreter.return_value.model_copy(update={"directives": ()})
    payload = {"base_revision_id": base, "request": "add a pool"}
    assert (
        client.post(f"/projects/{project}/revision-chat", headers=auth, json=payload).status_code
        == 422
    )
    interpreter.side_effect = RuntimeError("private provider payload")
    response = client.post(f"/projects/{project}/revision-chat", headers=auth, json=payload)
    assert response.status_code == 502
    assert "private provider payload" not in response.text
    assert len(client.get(f"/projects/{project}/revisions", headers=auth).json()) == 1


@pytest.mark.parametrize(
    "category,status",
    [
        (ProviderFailureCategory.TIMEOUT, 504),
        (ProviderFailureCategory.UNAVAILABLE, 503),
        (ProviderFailureCategory.INVALID_RESPONSE, 502),
    ],
)
def test_revision_provider_categories_without_retry(
    context: tuple[TestClient, Mock, dict[str, str], str, str],
    category: ProviderFailureCategory,
    status: int,
) -> None:
    client, interpreter, auth, project, base = context
    interpreter.side_effect = ProviderRuntimeError(category, "ollama_local")
    response = client.post(
        f"/projects/{project}/revision-chat",
        headers=auth,
        json={"base_revision_id": base, "request": "make kitchen wider"},
    )
    assert response.status_code == status
    interpreter.assert_called_once()
    assert len(client.get(f"/projects/{project}/revisions", headers=auth).json()) == 1


def test_revision_rejects_semantic_room_correction_and_extra_directive_fields(
    context: tuple[TestClient, Mock, dict[str, str], str, str],
) -> None:
    client, interpreter, auth, project, base = context
    original = interpreter.return_value
    for changes in ({"room_type": "Kitchen"}, {"target_mm": 6000}, {"delta_mm": 0}):
        interpreter.return_value = original.model_copy(
            update={
                "directives": (original.directives[0].model_copy(update=changes),),
            }
        )
        response = client.post(
            f"/projects/{project}/revision-chat",
            headers=auth,
            json={"base_revision_id": base, "request": "make kitchen wider"},
        )
        assert response.status_code == 422
    assert len(client.get(f"/projects/{project}/revisions", headers=auth).json()) == 1
