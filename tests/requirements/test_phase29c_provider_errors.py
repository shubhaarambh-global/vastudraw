from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from ai_vastu.openrouter_http import OpenRouterModelPolicy
from ai_vastu.provider_runtime import ProviderFailureCategory, ProviderRuntimeError
from ai_vastu.requirements.errors import RequirementsProviderError
from ai_vastu.requirements.providers.base import InterpretationInput
from ai_vastu.requirements.providers.openrouter_chat import OpenRouterRequirementsProvider
from ai_vastu.requirements.service import RequirementsService


class _FailingClient:
    def complete_validated_json(self, **_kwargs: object) -> object:
        raise ProviderRuntimeError(
            ProviderFailureCategory.TIMEOUT,
            "openrouter",
        )


def test_openrouter_requirements_adapter_preserves_sanitized_runtime_category() -> None:
    provider = OpenRouterRequirementsProvider(
        client=cast(Any, _FailingClient()),
        policy=OpenRouterModelPolicy(),
    )

    with pytest.raises(RequirementsProviderError) as captured:
        provider.interpret(
            InterpretationInput(
                draft_id=UUID("11111111-1111-1111-1111-111111111111"),
                user_id=UUID("22222222-2222-2222-2222-222222222222"),
                project_id=UUID("33333333-3333-3333-3333-333333333333"),
                prompt="private prompt",
                references=(),
            )
        )

    assert captured.value.category is ProviderFailureCategory.TIMEOUT
    assert "private prompt" not in str(captured.value)


def test_requirements_service_does_not_save_draft_after_provider_failure() -> None:
    provider = MagicMock()
    provider.interpret.side_effect = ProviderRuntimeError(
        ProviderFailureCategory.UNAVAILABLE,
        "openrouter",
    )
    store = MagicMock()
    service = RequirementsService(provider=provider, store=store)

    with pytest.raises(RequirementsProviderError) as captured:
        service.interpret(
            user_id=UUID("22222222-2222-2222-2222-222222222222"),
            project_id=UUID("33333333-3333-3333-3333-333333333333"),
            prompt="home",
            references=(),
        )

    assert captured.value.category is ProviderFailureCategory.UNAVAILABLE
    store.save_draft.assert_not_called()
