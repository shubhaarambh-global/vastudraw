class PlanIntakeError(RuntimeError):
    pass


class PlanIntakeConfigurationError(PlanIntakeError):
    pass


class PlanIntakeProviderError(PlanIntakeError):
    pass


class PlanAnalysisNotFoundError(LookupError):
    pass
