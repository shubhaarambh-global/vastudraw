from tests.exporting.helpers import export_plan

from ai_vastu.architectural_brain import build_fallback_concept
from ai_vastu.architectural_brain.candidate_engine import (
    _candidate_search_schedule,
    _distinct_documents,
)
from ai_vastu.multi_candidate import default_candidate_strategies
from ai_vastu.multi_candidate.strategies import search_variant_for_strategy


def _concepts():
    return tuple(
        build_fallback_concept(project_id=export_plan().project_id, room_types=("living",))
        for _ in range(6)
    )


def test_shortfall_explores_two_bounded_variants_without_changing_concepts():
    concepts = _concepts()
    strategies = default_candidate_strategies()
    schedule = list(_candidate_search_schedule(concepts, strategies, [], 4))
    assert len(schedule) == 12
    assert schedule[:6] == list(zip(concepts, strategies, strict=True))
    for index, (concept, alternate) in enumerate(schedule[6:]):
        assert concept is concepts[index]
        assert search_variant_for_strategy(alternate) != search_variant_for_strategy(
            strategies[index]
        )
    assert len({strategy.strategy_id for _, strategy in schedule}) == 12


def test_sufficient_material_candidates_do_not_expand_search():
    schedule = _candidate_search_schedule(
        _concepts(), default_candidate_strategies(), [export_plan()], 1
    )
    assert len(list(schedule)) == 6


def test_ids_and_hashes_do_not_manufacture_material_diversity():
    plan = export_plan()
    duplicate = plan.model_copy(update={"revision_id": plan.project_id, "content_hash": None})
    assert _distinct_documents([plan, duplicate]) == 1
    assert (
        len(
            list(
                _candidate_search_schedule(
                    _concepts(), default_candidate_strategies(), [plan, duplicate], 2
                )
            )
        )
        == 12
    )


def test_schedule_observes_candidates_accepted_during_first_pass():
    accepted = []
    schedule = _candidate_search_schedule(_concepts(), default_candidate_strategies(), accepted, 1)
    for _ in range(6):
        next(schedule)
    accepted.append(export_plan())
    assert list(schedule) == []
