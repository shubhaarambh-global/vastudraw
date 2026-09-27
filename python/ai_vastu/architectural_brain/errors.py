from __future__ import annotations

from ai_vastu.provider_runtime import ProviderFailureCategory, ProviderRuntimeError


class ArchitecturalBrainError(RuntimeError):
    pass


class ArchitecturalBrainConfigurationError(ArchitecturalBrainError):
    """Architectural Brain provider configuration is invalid."""


class ArchitecturalBrainProviderError(ArchitecturalBrainError):
    """Sanitized provider outage distinct from deterministic rejection."""

    def __init__(
        self,
        category: ProviderFailureCategory = ProviderFailureCategory.INVALID_RESPONSE,
    ) -> None:
        self.category = category
        super().__init__("Architectural Brain provider failed.")

    @classmethod
    def from_exception(cls, exc: BaseException) -> ArchitecturalBrainProviderError:
        current: BaseException | None = exc
        for _ in range(8):
            if current is None:
                break
            if isinstance(current, ProviderRuntimeError):
                return cls(current.category)
            current = current.__cause__ or current.__context__
        return cls(ProviderFailureCategory.INVALID_RESPONSE)
