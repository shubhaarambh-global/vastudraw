"""Versioned, deterministic Vastu rule infrastructure.

Phase 4 provides rule mechanics only. It intentionally contains no production
Vastu rule content. Production rules enter only after source/reviewer work in
Phase 5.
"""

from .compiler import compile_rule_bundle
from .errors import (
    RuleBundleIntegrityError,
    RuleConflictError,
    RuleSourceError,
    VastuRuleError,
)
from .evaluator import evaluate_bundle, evaluate_rule
from .facts import area_overlap_basis_points, make_area_overlap_fact
from .models import (
    BooleanPredicate,
    EnumSetPredicate,
    GeometrySemantic,
    NumericRangePredicate,
    PredicateKind,
    RuleBundle,
    RuleClassification,
    RuleEvaluation,
    RuleLifecycle,
    RuleSeverity,
    SourceRecord,
    SourceReference,
    SubjectAttribute,
    SubjectSelector,
    VastuFact,
    VastuRule,
)
from .source_registry import SourceRegistry

__all__ = [
    "BooleanPredicate",
    "EnumSetPredicate",
    "GeometrySemantic",
    "NumericRangePredicate",
    "PredicateKind",
    "RuleBundle",
    "RuleBundleIntegrityError",
    "RuleClassification",
    "RuleConflictError",
    "RuleEvaluation",
    "RuleLifecycle",
    "RuleSeverity",
    "RuleSourceError",
    "SourceRecord",
    "SourceReference",
    "SourceRegistry",
    "SubjectAttribute",
    "SubjectSelector",
    "VastuFact",
    "VastuRule",
    "VastuRuleError",
    "area_overlap_basis_points",
    "compile_rule_bundle",
    "evaluate_bundle",
    "evaluate_rule",
    "make_area_overlap_fact",
]
