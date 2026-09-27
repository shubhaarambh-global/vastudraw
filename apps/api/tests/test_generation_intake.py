from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from PIL import Image

from ai_vastu.auth import DevelopmentAccessTokenVerifier
from ai_vastu.generation_intake import GenerationIntakeStore
from ai_vastu.projects import SqliteProjectRepository
from app.main import create_app

PROJECT_ID = UUID("33333333-aaaa-bbbb-cccc-333333333333")
USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TOKEN = "generation-intake-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def _client(tmp_path: Path) -> TestClient:
    repository = SqliteProjectRepository(":memory:")
    return TestClient(
        create_app(
            repository,
            DevelopmentAccessTokenVerifier(TOKEN, USER_ID),
            GenerationIntakeStore(tmp_path / "generation-intakes"),
        )
    )


def _create_project(client: TestClient) -> None:
    response = client.post(
        "/projects",
        json={"name": "Client residence", "project_id": str(PROJECT_ID)},
        headers=AUTH,
    )
    assert response.status_code == 201


def test_generation_intake_upload_is_project_bound_and_loadable(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _create_project(client)

    created = client.post(
        f"/projects/{PROJECT_ID}/generation-intakes",
        headers=AUTH,
        data={"prompt": "3BHK home with a puja room and one-car parking."},
        files=[
            ("files", ("reference.jpg", _jpeg_bytes(), "image/jpeg")),
            (
                "files",
                ("survey.pdf", b"%PDF-1.7\nclient-pdf\n%%EOF\n", "application/pdf"),
            ),
        ],
    )
    assert created.status_code == 201
    body = created.json()
    assert body["project_id"] == str(PROJECT_ID)
    assert body["authoritative_geometry"] is False
    assert len(body["attachments"]) == 2

    listed = client.get(f"/projects/{PROJECT_ID}/generation-intakes", headers=AUTH)
    assert listed.status_code == 200
    assert [item["intake_id"] for item in listed.json()] == [body["intake_id"]]


def test_generation_intake_rejects_invalid_reference_bytes(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _create_project(client)
    response = client.post(
        f"/projects/{PROJECT_ID}/generation-intakes",
        headers=AUTH,
        data={"prompt": "Use this PDF as a client reference."},
        files=[("files", ("bad.pdf", b"plain text", "application/pdf"))],
    )
    assert response.status_code == 422
    assert "PDF attachment signature" in response.json()["detail"]
