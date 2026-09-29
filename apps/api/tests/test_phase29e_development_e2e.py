from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from ai_vastu.auth import DevelopmentAccessTokenVerifier
from ai_vastu.billing import PhonePeClient, RazorpayClient
from ai_vastu.billing.sqlite_repository import SqliteBillingRepository
from ai_vastu.generation_intake import GenerationIntakeStore
from ai_vastu.plan_schema import PlanDocument
from ai_vastu.projects import SqliteProjectRepository
from app.main import create_app

USER_ID = UUID("29e00000-0000-0000-0000-000000000001")
PROJECT_ID = UUID("29e00000-0000-0000-0000-000000000002")
TOKEN = "phase29e-development-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


def _image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format=image_format)
    return buffer.getvalue()


def _unexpected_provider_call(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("Development E2E attempted an external payment-provider call.")


def test_selection_rejects_malformed_plan_before_billing_or_provider_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    billing_path = tmp_path / "billing.sqlite3"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", "disabled")
    monkeypatch.setenv("AI_VASTU_DEV_BILLING_BYPASS", "1")
    monkeypatch.setenv("AI_VASTU_BILLING_SQLITE_PATH", str(billing_path))
    monkeypatch.setattr(PhonePeClient, "create_checkout", _unexpected_provider_call)
    monkeypatch.setattr(PhonePeClient, "get_order_status", _unexpected_provider_call)
    monkeypatch.setattr(RazorpayClient, "create_checkout", _unexpected_provider_call)

    repository = SqliteProjectRepository(":memory:")
    app = create_app(repository, DevelopmentAccessTokenVerifier(TOKEN, USER_ID))

    with TestClient(app) as client:
        created = client.post(
            "/projects",
            json={"name": "Malformed Selection", "project_id": str(PROJECT_ID)},
            headers=AUTH,
        )
        assert created.status_code == 201

        rejected = client.post(
            f"/confirmed-generation/projects/{PROJECT_ID}/alternatives/select",
            headers=AUTH,
            json={
                "draft_id": str(uuid4()),
                "candidate_run_hash": "0" * 64,
                "candidate_id": str(uuid4()),
                "plan_document": {"schema_version": "1.1.0"},
            },
        )

    assert rejected.status_code == 422
    assert not billing_path.exists()


def test_phase29e_development_e2e_uses_bypass_without_payment_provider_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requirements_path = tmp_path / "requirements"
    intake_path = tmp_path / "generation-intakes"
    billing_path = tmp_path / "billing.sqlite3"

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AI_VASTU_PAYMENT_GATEWAY", "disabled")
    monkeypatch.setenv("AI_VASTU_DEV_BILLING_BYPASS", "1")
    monkeypatch.setenv("AI_VASTU_BILLING_SQLITE_PATH", str(billing_path))
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PATH", str(requirements_path))
    monkeypatch.setenv("AI_VASTU_GENERATION_UPLOAD_ROOT", str(intake_path))
    monkeypatch.setenv("AI_VASTU_REQUIREMENTS_PROVIDER", "fixture")
    monkeypatch.setenv("AI_VASTU_PLAN_RECOGNITION_PROVIDER", "fixture")
    monkeypatch.setenv("AI_VASTU_ARCHITECT_PROVIDER", "fixture")
    monkeypatch.setenv("AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER", "fixture")
    monkeypatch.setenv("AI_VASTU_VASTU_PROVIDER", "fixture")
    monkeypatch.setenv("AI_VASTU_REVISION_PROVIDER", "fixture")
    for name in (
        "AI_VASTU_PHONEPE_CLIENT_ID",
        "AI_VASTU_PHONEPE_CLIENT_SECRET",
        "AI_VASTU_PHONEPE_WEBHOOK_USERNAME",
        "AI_VASTU_PHONEPE_WEBHOOK_PASSWORD",
        "AI_VASTU_RAZORPAY_KEY_ID",
        "AI_VASTU_RAZORPAY_KEY_SECRET",
        "AI_VASTU_RAZORPAY_WEBHOOK_SECRET",
        "OPENROUTER_API_KEY",
        "GEMINI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setattr(PhonePeClient, "create_checkout", _unexpected_provider_call)
    monkeypatch.setattr(PhonePeClient, "get_order_status", _unexpected_provider_call)
    monkeypatch.setattr(RazorpayClient, "create_checkout", _unexpected_provider_call)

    repository = SqliteProjectRepository(":memory:")
    app = create_app(
        repository,
        DevelopmentAccessTokenVerifier(TOKEN, USER_ID),
        GenerationIntakeStore(intake_path),
    )

    with TestClient(app) as client:
        created = client.post(
            "/projects",
            json={"name": "Phase 29E Development Home", "project_id": str(PROJECT_ID)},
            headers=AUTH,
        )
        assert created.status_code == 201

        intake = client.post(
            f"/projects/{PROJECT_ID}/generation-intakes",
            headers=AUTH,
            data={"prompt": "30 x 50 ft, east road, one bedroom."},
            files=[
                ("files", ("reference.jpg", _image_bytes("JPEG"), "image/jpeg")),
                ("files", ("reference.png", _image_bytes("PNG"), "image/png")),
                ("files", ("survey.pdf", b"%PDF-1.7\nphase29e\n%%EOF\n", "application/pdf")),
            ],
        )
        assert intake.status_code == 201
        intake_id = intake.json()["intake_id"]

        analysis = client.post(
            f"/projects/{PROJECT_ID}/generation-intakes/{intake_id}/plan-analysis",
            headers=AUTH,
        )
        assert analysis.status_code == 200
        assert analysis.json()["recognition"]["provider"] == "fixture"
        assert analysis.json()["recognition"]["envelope"]["requires_confirmation"] is True

        confirmation = client.post(
            f"/projects/{PROJECT_ID}/generation-intakes/{intake_id}/plan-confirmation",
            headers=AUTH,
            json={
                "width_mm": 9144,
                "depth_mm": 15240,
                "north_rotation_deg": 0,
                "road_side": "E",
                "entrance_facing": "E",
                "preserve_outer_envelope": True,
            },
        )
        assert confirmation.status_code == 200
        assert confirmation.json()["confirmed_by_user"] is True

        interpreted = client.post(
            "/requirements/interpret",
            headers=AUTH,
            data={
                "project_id": str(PROJECT_ID),
                "prompt": (
                    "30 x 50 ft, road on east, true north 0 deg, 1 BHK, "
                    "kitchen and dining."
                ),
            },
        )
        assert interpreted.status_code == 200
        draft = interpreted.json()["draft"]
        assert draft["provider"] == "fixture"
        assert interpreted.json()["ready_for_confirmation"] is True

        draft_id = draft["draft_id"]
        confirmed = client.post(
            f"/requirements/drafts/{draft_id}/confirm",
            headers=AUTH,
            json={
                "draft_id": draft_id,
                "user_id": str(USER_ID),
                "project_id": str(PROJECT_ID),
                "user_confirmed": True,
                "plot_width_mm": 9144,
                "plot_depth_mm": 15240,
                "north_rotation_deg": 0,
                "road_side": "E",
                "entrance_facing": "E",
                "floor_count": 1,
                "bedroom_count": 1,
                "parking_count": 0,
                "vastu_mode": "balanced",
                "rooms": [
                    {"room_type": "bedroom", "quantity": 1},
                    {"room_type": "kitchen", "quantity": 1},
                    {"room_type": "dining", "quantity": 1},
                ],
            },
        )
        assert confirmed.status_code == 200

        alternatives = client.post(
            f"/confirmed-generation/projects/{PROJECT_ID}/alternatives",
            headers=AUTH,
            json={
                "draft_id": draft_id,
                "accept_profile_defaults": True,
                "max_alternatives": 1,
            },
        )
        assert alternatives.status_code == 200, alternatives.text
        preview = alternatives.json()
        assert preview["billing_reason"] == "development_bypass"
        assert preview["quota_consumed"] is False
        assert preview["revision_persisted"] is False
        run = preview["candidate_run"]
        assert run["candidates"]
        candidate = run["candidates"][0]
        assert candidate["valid_architecture"] is True
        assert candidate["plan_document"]["validation"]["valid"] is True

        selected = client.post(
            f"/confirmed-generation/projects/{PROJECT_ID}/alternatives/select",
            headers=AUTH,
            json={
                "draft_id": draft_id,
                "candidate_run_hash": run["content_hash"],
                "candidate_id": candidate["candidate_id"],
                "plan_document": candidate["plan_document"],
            },
        )
        assert selected.status_code == 200, selected.text
        selection = selected.json()
        assert selection["billing_reason"] == "development_bypass"
        assert selection["revision_persisted"] is True
        assert selection["successful_generation_recorded"] is True

        persisted = client.get(
            f"/projects/{PROJECT_ID}/revisions/{selection['revision_id']}",
            headers=AUTH,
        )
        assert persisted.status_code == 200
        persisted_document = PlanDocument.model_validate_json(
            json.dumps(persisted.json()["document"], sort_keys=True, separators=(",", ":"))
        )
        assert persisted_document.content_hash == selection["plan_document_hash"]

        revised_document = persisted_document.model_copy(
            update={"revision_id": uuid4(), "content_hash": None}
        ).with_content_hash()
        revised = client.post(
            f"/projects/{PROJECT_ID}/revisions",
            headers=AUTH,
            json={
                "document": revised_document.model_dump(mode="json"),
                "expected_parent_revision_id": selection["revision_id"],
                "source_candidate_id": selection["candidate_id"],
                "note": "Phase 29E deterministic local revision.",
            },
        )
        assert revised.status_code == 201, revised.text
        assert revised.json()["revision_number"] == 2

        exported = client.post(
            f"/projects/{PROJECT_ID}/exports",
            headers=AUTH,
            json={
                "revision_id": revised.json()["revision_id"],
                "candidate_id": selection["candidate_id"],
                "format": "PDF",
                "scope": "ALL_FLOORS",
                "floor_index": None,
            },
        )
        assert exported.status_code == 200, exported.text
        assert exported.content.startswith(b"%PDF-")
        assert exported.headers["x-vastudraw-source-hash"] == revised_document.content_hash

    billing_repository = SqliteBillingRepository(billing_path)
    try:
        snapshot = billing_repository.get_snapshot(str(USER_ID))
        assert snapshot.free_generation_available is True
        assert snapshot.project_credits == 0
    finally:
        billing_repository.close()
