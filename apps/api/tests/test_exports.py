from __future__ import annotations

import re
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from tests.exporting.test_professional_renderer import professional_plan

from ai_vastu.auth import DevelopmentAccessTokenVerifier
from ai_vastu.exporting import ProductionExportError
from ai_vastu.projects import AppendRevisionCommand, ProjectRevisionService, SqliteProjectRepository
from app.main import create_app

USER_A = UUID("aaaaaaaa-1111-1111-1111-111111111111")
USER_B = UUID("bbbbbbbb-2222-2222-2222-222222222222")
PROJECT_A = UUID("cccccccc-3333-3333-3333-333333333333")
PROJECT_B = UUID("dddddddd-4444-4444-4444-444444444444")
CANDIDATE_A = UUID("eeeeeeee-5555-5555-5555-555555555555")
CANDIDATE_B = UUID("ffffffff-6666-6666-6666-666666666666")
TOKEN_A = "export-token-a"
TOKEN_B = "export-token-b"


def _client(
    repository: SqliteProjectRepository,
    *,
    user_id: UUID = USER_A,
    token: str = TOKEN_A,
) -> TestClient:
    return TestClient(create_app(repository, DevelopmentAccessTokenVerifier(token, user_id)))


def _seed_selected_revision(
    repository: SqliteProjectRepository,
    *,
    project_id: UUID = PROJECT_A,
    owner_id: UUID = USER_A,
    candidate_id: UUID = CANDIDATE_A,
    floors: int = 1,
):
    service = ProjectRevisionService(repository)
    service.create_project("Sharma Residence", project_id, owner_id)
    source = professional_plan(floors=floors)
    document = source.model_copy(
        update={
            "project_id": project_id,
            "content_hash": None,
        }
    ).with_content_hash()
    revision = service.append_revision(
        AppendRevisionCommand(
            project_id=project_id,
            document=document,
            source_candidate_id=candidate_id,
            note="Selected deterministic candidate.",
        )
    )
    return revision


def _payload(revision_id: UUID, candidate_id: UUID, export_format: str) -> dict[str, object]:
    return {
        "revision_id": str(revision_id),
        "candidate_id": str(candidate_id),
        "format": export_format,
        "scope": "FLOOR",
        "floor_index": 0,
    }


@pytest.mark.parametrize(
    ("export_format", "media_type"),
    [
        ("SVG", "image/svg+xml"),
        ("JPEG", "image/jpeg"),
        ("PDF", "application/pdf"),
        ("DXF", "application/dxf"),
    ],
)
def test_selected_candidate_downloads_supported_artifact(
    export_format: str,
    media_type: str,
) -> None:
    repository = SqliteProjectRepository(":memory:")
    revision = _seed_selected_revision(repository)
    response = _client(repository).post(
        f"/projects/{PROJECT_A}/exports",
        json=_payload(revision.revision_id, CANDIDATE_A, export_format),
        headers={"Authorization": f"Bearer {TOKEN_A}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == media_type
    assert response.headers["x-vastudraw-candidate-id"] == str(CANDIDATE_A)
    assert response.headers["x-vastudraw-source-hash"] == revision.plan_document_hash
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="vastudraw-sharma-residence-ground-floor.'
    )
    assert "\\" not in response.headers["content-disposition"]
    assert ":" not in response.headers["content-disposition"]


def test_combined_download_is_a_true_ordered_multi_page_pdf() -> None:
    repository = SqliteProjectRepository(":memory:")
    revision = _seed_selected_revision(repository, floors=4)
    response = _client(repository).post(
        f"/projects/{PROJECT_A}/exports",
        json={
            "revision_id": str(revision.revision_id),
            "candidate_id": str(CANDIDATE_A),
            "format": "PDF",
            "scope": "ALL_FLOORS",
            "floor_index": None,
        },
        headers={"Authorization": f"Bearer {TOKEN_A}"},
    )

    assert response.status_code == 200
    assert len(re.findall(rb"/Type /Page(?!s)", response.content)) == 4
    assert response.headers["x-vastudraw-combined"] == "true"
    assert response.headers["x-vastudraw-floor-index"] == "all"
    assert response.headers["content-disposition"] == (
        'attachment; filename="vastudraw-sharma-residence-all-floors.pdf"'
    )


def test_project_and_candidate_identity_are_enforced_server_side() -> None:
    repository = SqliteProjectRepository(":memory:")
    revision_a = _seed_selected_revision(repository)
    service = ProjectRevisionService(repository)
    service.create_project("Other Home", PROJECT_B, USER_B)

    owner = _client(repository)
    candidate_mismatch = owner.post(
        f"/projects/{PROJECT_A}/exports",
        json=_payload(revision_a.revision_id, CANDIDATE_B, "PDF"),
        headers={"Authorization": f"Bearer {TOKEN_A}"},
    )
    assert candidate_mismatch.status_code == 404
    assert candidate_mismatch.json()["detail"] == (
        "The selected candidate revision does not exist."
    )

    other_user = _client(repository, user_id=USER_B, token=TOKEN_B)
    unauthorized = other_user.post(
        f"/projects/{PROJECT_A}/exports",
        json=_payload(revision_a.revision_id, CANDIDATE_A, "PDF"),
        headers={"Authorization": f"Bearer {TOKEN_B}"},
    )
    assert unauthorized.status_code == 404

    cross_project = other_user.post(
        f"/projects/{PROJECT_B}/exports",
        json=_payload(revision_a.revision_id, CANDIDATE_A, "PDF"),
        headers={"Authorization": f"Bearer {TOKEN_B}"},
    )
    assert cross_project.status_code == 404
    assert "revision" in cross_project.json()["detail"].lower()


@pytest.mark.parametrize("unsafe", ["PNG", "../../PDF", "PDF.exe", "pdf/../svg"])
def test_unsupported_or_path_like_format_is_rejected(unsafe: str) -> None:
    repository = SqliteProjectRepository(":memory:")
    revision = _seed_selected_revision(repository)
    response = _client(repository).post(
        f"/projects/{PROJECT_A}/exports",
        json=_payload(revision.revision_id, CANDIDATE_A, unsafe),
        headers={"Authorization": f"Bearer {TOKEN_A}"},
    )
    assert response.status_code == 422


def test_export_failure_is_bounded_and_returns_no_partial_artifact(monkeypatch) -> None:
    repository = SqliteProjectRepository(":memory:")
    revision = _seed_selected_revision(repository)

    def fail_export(*_args, **_kwargs):
        raise ProductionExportError("EXPORT_RENDER_FAILED", "Rendering is unavailable.")

    monkeypatch.setattr("app.main.export_selected_document", fail_export)
    response = _client(repository).post(
        f"/projects/{PROJECT_A}/exports",
        json=_payload(revision.revision_id, CANDIDATE_A, "PDF"),
        headers={"Authorization": f"Bearer {TOKEN_A}"},
    )
    assert response.status_code == 422
    assert response.json() == {
        "detail": "EXPORT_RENDER_FAILED: Rendering is unavailable."
    }
    assert "content-disposition" not in response.headers
