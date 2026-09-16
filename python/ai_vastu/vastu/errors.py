from __future__ import annotations


class VastuRuleError(RuntimeError):
    """Base error for deterministic Vastu rule infrastructure."""


class RuleSourceError(VastuRuleError):
    """Raised when a rule references missing or invalid provenance."""


class RuleConflictError(VastuRuleError):
    """Raised when production hard rules are mutually contradictory."""


class RuleBundleIntegrityError(VastuRuleError):
    """Raised when a compiled bundle's deterministic hash does not verify."""
