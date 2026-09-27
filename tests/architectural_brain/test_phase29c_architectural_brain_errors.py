from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from tests.requirements.test_phase26c4a_residential_planning import _confirmed

from ai_vastu.architectural_brain import candidate_engine
from ai_vastu.architectural_brain.errors import ArchitecturalBrainProviderError
from ai_vastu.architectural_brain.provider import GeminiArchitecturalBrainProvider
from ai_vastu.architectural_brain.revisions import interpret_revision_with_gemini
from ai_vastu.provider_runtime import ProviderFailureCategory
from ai_vastu.requirements.generation_adapter import compile_confirmed_requirements


class _FailingBrainService:
    def propose(self, **_kwargs: object) -> object:
        raise ArchitecturalBrainProviderError(ProviderFailureCategory.TIMEOUT)


def test_provider_outage_bypasses_deterministic_candidate_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    confirmed = _confirmed()
    compiled = compile_confirmed_requirements(confirmed)
    monkeypatch.setattr(
        "ai_vastu.architectural_brain.candidate_engine."
        "ArchitecturalBrainService.from_environment",
        lambda: _FailingBrainService(),
    )

    with pytest.raises(ArchitecturalBrainProviderError) as captured:
        candidate_engine.run_architectural_brain_candidates(
            confirmed=confirmed,
            compiled=compiled,
            original_prompt="home",
            vastu_profile=None,
            precedent_matches=(),
            max_alternatives=2,
        )

    assert captured.value.category is ProviderFailureCategory.TIMEOUT


def test_legacy_gemini_brain_key_is_header_only_and_absent_from_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "phase29c-secret-never-in-url"
    seen: dict[str, object] = {}

    def failing_post(url: str, **kwargs: object) -> httpx.Response:
        seen["url"] = url
        seen["headers"] = kwargs.get("headers")
        return httpx.Response(401, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", failing_post)
    provider = GeminiArchitecturalBrainProvider(
        api_key=secret,
        model="gemini-3.1-flash-lite",
    )

    with pytest.raises(ArchitecturalBrainProviderError) as captured:
        provider.propose(
            project_id=UUID("11111111-1111-1111-1111-111111111111"),
            original_prompt="private prompt",
            width_mm=9_000,
            depth_mm=12_000,
            bedroom_count=2,
            toilet_count=2,
            parking_count=1,
            room_types=("living", "kitchen", "bedroom"),
            road_side="NORTH",
            entrance_side="NORTH",
            precedents=(),
            concept_count=2,
        )

    assert seen["headers"] == {"x-goog-api-key": secret}
    assert secret not in str(seen["url"])
    assert secret not in str(captured.value)
    assert secret not in str(captured.value.__cause__)


def test_legacy_gemini_revision_key_is_header_only_and_absent_from_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "phase29c-secret-never-in-url"
    seen: dict[str, object] = {}

    def failing_post(url: str, **kwargs: object) -> httpx.Response:
        seen["url"] = url
        seen["headers"] = kwargs.get("headers")
        return httpx.Response(401, request=httpx.Request("POST", url))

    monkeypatch.setenv("GEMINI_API_KEY", secret)
    monkeypatch.setattr(httpx, "post", failing_post)

    with pytest.raises(httpx.HTTPStatusError) as captured:
        interpret_revision_with_gemini(
            project_id=UUID("11111111-1111-1111-1111-111111111111"),
            base_revision_id=UUID("22222222-2222-2222-2222-222222222222"),
            request="private revision",
        )

    assert seen["headers"] == {"x-goog-api-key": secret}
    assert secret not in str(seen["url"])
    assert secret not in str(captured.value)
