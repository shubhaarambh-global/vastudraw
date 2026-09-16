class GenerationPipelineError(RuntimeError):
    """Base error for deterministic generation orchestration failures."""


class GenerationInputError(GenerationPipelineError):
    """Raised when explicit generation input cannot be compiled or executed."""
