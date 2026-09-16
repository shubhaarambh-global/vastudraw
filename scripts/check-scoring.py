from uuid import UUID

from scoring_smoke_fixture import candidate, problem

from ai_vastu.scoring import ScoringConfig, ScoringRequest, score_and_select_alternatives

first_candidate = candidate(UUID("a3000000-0000-0000-0000-000000000001"))
second_candidate = candidate(
    UUID("a3000000-0000-0000-0000-000000000002"),
    swapped=True,
)
request = ScoringRequest(
    problem=problem(),
    config=ScoringConfig(
        max_alternatives=3,
        room_change_threshold_mm=100,
        minimum_changed_rooms=2,
        reject_validation_warnings=False,
    ),
    candidates=(first_candidate, second_candidate),
)
first = score_and_select_alternatives(request)
second = score_and_select_alternatives(request)
if first != second or first.content_hash != second.content_hash:
    raise SystemExit("Architectural scoring/selection is not deterministic.")
if len(first.selected) != 2:
    raise SystemExit("Expected two diverse Phase 10 alternatives in scoring smoke.")
print(
    "Architectural scoring deterministic: "
    f"selected={len(first.selected)}, score={first.selected[0].candidate.overall_basis_points}, "
    f"hash={first.content_hash}"
)
