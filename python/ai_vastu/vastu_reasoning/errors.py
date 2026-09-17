class VastuReasoningError(RuntimeError):
    """Base Phase 26B Vastu reasoning error."""


class VastuReasoningConfigurationError(VastuReasoningError):
    """Vastu reasoning provider configuration is invalid."""


class VastuReasoningProviderError(VastuReasoningError):
    """Configured Vastu reasoning provider failed."""
