class ArchitecturalIntelligenceError(RuntimeError):
    """Base error for Phase 26A architectural reasoning."""


class ArchitecturalIntelligenceConfigurationError(ArchitecturalIntelligenceError):
    """Provider configuration is incomplete or invalid."""


class ArchitecturalIntelligenceProviderError(ArchitecturalIntelligenceError):
    """The configured reasoning provider failed or returned invalid output."""
