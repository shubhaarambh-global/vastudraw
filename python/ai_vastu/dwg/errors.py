class DwgError(RuntimeError):
    """Base error for the Phase 14 DWG qualification boundary."""


class DwgBackendUnavailableError(DwgError):
    """Raised when no configured DWG backend is available."""


class DwgBackendNotQualifiedError(DwgError):
    """Raised when an export is attempted with an unqualified backend."""


class DwgBackendExecutionError(DwgError):
    """Raised when an external backend process fails."""


class DwgInspectionError(DwgError):
    """Raised when DWG inspection evidence is malformed or incomplete."""
