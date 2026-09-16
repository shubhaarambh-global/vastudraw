from __future__ import annotations


class ExportError(ValueError):
    """Base error for deterministic plan export."""


class ExportSceneError(ExportError):
    """Raised when a canonical plan cannot produce a DrawingScene."""


class ExportRenderError(ExportError):
    """Raised when an exporter cannot render a valid DrawingScene."""
