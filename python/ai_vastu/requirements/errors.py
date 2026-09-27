from __future__ import annotations

from ai_vastu.provider_runtime import ProviderFailureCategory, ProviderRuntimeError


class RequirementsConfigurationError(RuntimeError):
    """Requirements provider configuration is incomplete or invalid."""


class RequirementsProviderError(RuntimeError):
    """Sanitized requirements-provider failure with a stable category."""

    def __init__(
        self,
        category: ProviderFailureCategory = ProviderFailureCategory.INVALID_RESPONSE,
    ) -> None:
        self.category = category
        super().__init__("Requirements interpretation provider failed.")

    @classmethod
    def from_exception(cls, exc: BaseException) -> RequirementsProviderError:
        current: BaseException | None = exc
        for _ in range(8):
            if current is None:
                break
            if isinstance(current, ProviderRuntimeError):
                return cls(current.category)
            current = current.__cause__ or current.__context__
        return cls(ProviderFailureCategory.INVALID_RESPONSE)
