from __future__ import annotations

from ai_vastu.provider_runtime import ProviderFailureCategory, ProviderRuntimeError


class VastuReasoningError(RuntimeError):
    """Base Phase 26B Vastu reasoning error."""


class VastuReasoningConfigurationError(VastuReasoningError):
    """Vastu reasoning provider configuration is invalid."""


class VastuReasoningProviderError(VastuReasoningError):
    """Configured Vastu reasoning provider failed."""

    def __init__(
        self,
        category: ProviderFailureCategory | str = ProviderFailureCategory.INVALID_RESPONSE,
    ) -> None:
        self.category = (
            category
            if isinstance(category, ProviderFailureCategory)
            else ProviderFailureCategory.INVALID_RESPONSE
        )
        super().__init__("Vastu reasoning provider failed.")

    @classmethod
    def from_exception(cls, exc: BaseException) -> VastuReasoningProviderError:
        current: BaseException | None = exc
        for _ in range(8):
            if current is None:
                break
            if isinstance(current, ProviderRuntimeError):
                return cls(current.category)
            current = current.__cause__ or current.__context__
        return cls(ProviderFailureCategory.INVALID_RESPONSE)
