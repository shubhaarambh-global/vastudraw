from ai_vastu.dwg import (
    DwgTargetVersion,
    builtin_backend_candidates,
    preferred_production_candidate,
)


def test_oda_is_the_preferred_production_candidate() -> None:
    candidate = preferred_production_candidate()
    assert candidate.backend_id == "oda-drawings-sdk"
    assert candidate.modern_dwg_write is True
    assert DwgTargetVersion.R2018 in candidate.supported_targets
    assert candidate.bundled is False


def test_libredwg_is_not_accepted_for_r2018_production_write() -> None:
    candidate = next(
        item
        for item in builtin_backend_candidates()
        if item.backend_id == "gnu-libredwg"
    )
    assert candidate.production_candidate is False
    assert candidate.modern_dwg_write is False
    assert DwgTargetVersion.R2018 not in candidate.supported_targets
