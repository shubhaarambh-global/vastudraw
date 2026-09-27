from __future__ import annotations

from ai_vastu.provider_runtime import ProviderFailureCategory, ProviderRuntimeError


class PlanIntakeError(RuntimeError):
    pass


class PlanIntakeConfigurationError(PlanIntakeError):
    pass


class PlanIntakeProviderError(PlanIntakeError):
    def __init__(
        self,
        category: ProviderFailureCategory | str = ProviderFailureCategory.INVALID_RESPONSE,
    ) -> None:
        self.category = (
            category
            if isinstance(category, ProviderFailureCategory)
            else ProviderFailureCategory.INVALID_RESPONSE
        )
        super().__init__("Plan recognition provider failed.")

    @classmethod
    def from_exception(cls, exc: BaseException) -> PlanIntakeProviderError:
        current: BaseException | None = exc
        for _ in range(8):
            if current is None:
                break
            if isinstance(current, ProviderRuntimeError):
                return cls(current.category)
            current = current.__cause__ or current.__context__
        return cls(ProviderFailureCategory.INVALID_RESPONSE)


class PlanAnalysisNotFoundError(LookupError):
    pass
