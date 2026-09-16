from __future__ import annotations


class VastuSpecError(RuntimeError):
    """Base error for Vastu Specification authoring/release validation."""


class VastuSpecLoadError(VastuSpecError):
    """Raised when repository authoring files are missing or malformed."""


class VastuSpecApprovalError(VastuSpecError):
    """Raised when review/approval requirements are not satisfied."""


class VastuSpecIntegrityError(VastuSpecError):
    """Raised when hashes, IDs, or release metadata do not reconcile."""
