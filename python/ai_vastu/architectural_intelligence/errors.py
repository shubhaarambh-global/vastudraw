from __future__ import annotations

from ai_vastu.provider_runtime import ProviderFailureCategory, ProviderRuntimeError


class ArchitecturalIntelligenceError(RuntimeError):
    """Base error for Phase 26A architectural reasoning."""


class ArchitecturalIntelligenceConfigurationError(ArchitecturalIntelligenceError):
    """Provider configuration is incomplete or invalid."""


class ArchitecturalIntelligenceProviderError(ArchitecturalIntelligenceError):
    """The configured reasoning provider failed or returned invalid output."""

    def __init__(
        self,
        category: ProviderFailureCategory | str = ProviderFailureCategory.INVALID_RESPONSE,
    ) -> None:
        self.category = (
            category
            if isinstance(category, ProviderFailureCategory)
            else ProviderFailureCategory.INVALID_RESPONSE
        )
        super().__init__("Architectural reasoning provider failed.")

    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
    ) -> ArchitecturalIntelligenceProviderError:
        current: BaseException | None = exc
        for _ in range(8):
            if current is None:
                break
            if isinstance(current, ProviderRuntimeError):
                return cls(current.category)
            current = current.__cause__ or current.__context__
        return cls(ProviderFailureCategory.INVALID_RESPONSE)
