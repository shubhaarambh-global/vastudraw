from __future__ import annotations

from ai_vastu.plan_schema import VastuStatus
from ai_vastu.vastu import (
    GeometrySemantic,
    RuleLifecycle,
    SourceRegistry,
    SubjectAttribute,
    VastuFact,
    compile_rule_bundle,
    evaluate_bundle,
)

from .helpers import numeric_rule, source


def test_numeric_rule_uses_measured_fact_evidence() -> None:
    rule = numeric_rule()
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=SourceRegistry((source(),)),
        rules=(rule,),
    )
    evaluations = evaluate_bundle(
        bundle,
        (
            VastuFact(
                entity_id="space-01",
                entity_type="synthetic_space",
                geometry_semantic=GeometrySemantic.AREA_OVERLAP_PERCENT,
                metric_key="synthetic_zone_overlap_bp",
                value=9_250,
                evidence=("overlap_area2=18500",),
            ),
        ),
    )
    assert len(evaluations) == 1
    assert evaluations[0].status is VastuStatus.PASS
    assert evaluations[0].earned_weight == 100
    assert evaluations[0].evidence == ("overlap_area2=18500",)


def test_failed_rule_never_earns_weight() -> None:
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=SourceRegistry((source(),)),
        rules=(numeric_rule(),),
    )
    evaluation = evaluate_bundle(
        bundle,
        (
            VastuFact(
                entity_id="space-01",
                entity_type="synthetic_space",
                geometry_semantic=GeometrySemantic.AREA_OVERLAP_PERCENT,
                metric_key="synthetic_zone_overlap_bp",
                value=2_000,
            ),
        ),
    )[0]
    assert evaluation.status is VastuStatus.FAIL
    assert evaluation.earned_weight == 0


def test_missing_fact_is_not_applicable_not_invented() -> None:
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=SourceRegistry((source(),)),
        rules=(numeric_rule(),),
    )
    evaluation = evaluate_bundle(bundle, ())[0]
    assert evaluation.status is VastuStatus.NOT_APPLICABLE
    assert evaluation.actual_value is None
    assert evaluation.entity_id is None


def test_subject_attributes_scope_evaluation() -> None:
    attribute = SubjectAttribute(key="synthetic_variant", value="A")
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=SourceRegistry((source(),)),
        rules=(numeric_rule(attributes=(attribute,)),),
    )
    facts = (
        VastuFact(
            entity_id="space-A",
            entity_type="synthetic_space",
            attributes=(attribute,),
            geometry_semantic=GeometrySemantic.AREA_OVERLAP_PERCENT,
            metric_key="synthetic_zone_overlap_bp",
            value=9_000,
        ),
        VastuFact(
            entity_id="space-B",
            entity_type="synthetic_space",
            attributes=(SubjectAttribute(key="synthetic_variant", value="B"),),
            geometry_semantic=GeometrySemantic.AREA_OVERLAP_PERCENT,
            metric_key="synthetic_zone_overlap_bp",
            value=9_000,
        ),
    )
    evaluations = evaluate_bundle(bundle, facts)
    assert [item.entity_id for item in evaluations] == ["space-A"]


def test_non_frozen_rule_cannot_affect_production_evaluation() -> None:
    bundle = compile_rule_bundle(
        spec_version="1.0.0",
        source_registry=SourceRegistry((source(),)),
        rules=(numeric_rule(lifecycle=RuleLifecycle.DRAFT),),
        production=True,
    )
    assert bundle.rules == ()
    assert evaluate_bundle(bundle, ()) == ()
