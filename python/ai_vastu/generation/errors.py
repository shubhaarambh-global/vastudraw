class GenerationPipelineError(RuntimeError):
    """Base error for deterministic generation orchestration failures."""


class GenerationInputError(GenerationPipelineError):
    """Raised when explicit generation input cannot be compiled or executed."""


class CirculationGenerationError(GenerationInputError):
    """Raised when solved geometry cannot support a valid dwelling access graph."""
