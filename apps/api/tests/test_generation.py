from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from ai_vastu.architectural_geometry import WallBuildConfig
from ai_vastu.auth import DevelopmentAccessTokenVerifier
from ai_vastu.generation import ArchitecturalGenerationRequest
from ai_vastu.plan_schema import BuildableArea, IntPoint, IntPolygon, RoomRequirement, RoomType
from ai_vastu.solver import PlannerConfig
from ai_vastu.validation import ValidationConfig
from app.main import create_app

TOKEN = "generation-test-token"
USER_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa19")
AUTH = {"Authorization": f"Bearer {TOKEN}", "content-type": "application/json"}


def _client() -> TestClient:
    return TestClient(
        create_app(access_token_verifier=DevelopmentAccessTokenVerifier(TOKEN, USER_ID))
    )


def _request() -> ArchitecturalGenerationRequest:
    boundary = IntPolygon(
        outer=(
            IntPoint(x_mm=0, y_mm=0),
            IntPoint(x_mm=9000, y_mm=0),
            IntPoint(x_mm=9000, y_mm=7000),
            IntPoint(x_mm=0, y_mm=7000),
        )
    )
    return ArchitecturalGenerationRequest(
        plot_boundary=boundary,
        buildable_area=BuildableArea(polygon=boundary),
        room_requirements=(
            RoomRequirement(
                id=UUID("b6200000-0000-0000-0000-000000000001"),
                room_type=RoomType.LIVING,
                min_width_mm=3000,
                preferred_width_mm=3600,
                max_width_mm=4500,
                min_depth_mm=3000,
                preferred_depth_mm=3600,
                max_depth_mm=4500,
                min_area_mm2=10_000_000,
                user_priority=80,
            ),
            RoomRequirement(
                id=UUID("b6200000-0000-0000-0000-000000000002"),
                room_type=RoomType.DINING,
                min_width_mm=2700,
                preferred_width_mm=3000,
                max_width_mm=4000,
                min_depth_mm=2700,
                preferred_depth_mm=3000,
                max_depth_mm=4000,
                min_area_mm2=8_000_000,
                user_priority=70,
            ),
        ),
        floor_id=UUID("b6200000-0000-0000-0000-000000000010"),
        floor_name="Ground Floor",
        floor_index=0,
        elevation_mm=0,
        floor_to_floor_mm=3300,
        wall_config=WallBuildConfig(
            external_wall_thickness_mm=230,
            internal_wall_thickness_mm=115,
            wall_height_mm=3000,
        ),
        planner_config=PlannerConfig(
            solver_step_mm=100,
            max_time_ms=5000,
            max_conflicts=100000,
            random_seed=19,
        ),
        validation_config=ValidationConfig(
            tiny_sliver_area_mm2=10_000,
            door_clearance_margin_mm=50,
        ),
    )


def test_architectural_generation_endpoint_runs_deterministic_pipeline() -> None:
    client = _client()
    payload = _request().model_dump_json()

    first = client.post(
        "/generation/architectural",
        content=payload,
        headers=AUTH,
    )
    second = client.post(
        "/generation/architectural",
        content=payload,
        headers=AUTH,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body["disposition"] == "REJECTED"
    assert body["validation_result"]["report"]["valid"] is False
    codes = {item["message_code"] for item in body["validation_result"]["report"]["errors"]}
    assert "UNREACHABLE_ROOM_FROM_EXTERIOR_ACCESS" in codes
    assert len(body["geometry_result"]["floor"]["rooms"]) == 2
    assert body["content_hash"] is not None


def test_architectural_generation_endpoint_rejects_invalid_json_model() -> None:
    client = _client()
    response = client.post(
        "/generation/architectural",
        content='{"floor_name":"Ground Floor"}',
        headers=AUTH,
    )
    assert response.status_code == 422
