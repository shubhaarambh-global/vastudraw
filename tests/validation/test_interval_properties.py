from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ai_vastu.validation.validator import _interval_covered


@given(
    start=st.integers(min_value=0, max_value=20),
    length=st.integers(min_value=1, max_value=20),
    split=st.integers(min_value=0, max_value=20),
)
def test_exact_interval_coverage_is_stable_under_segment_splitting(
    start: int,
    length: int,
    split: int,
) -> None:
    end = start + length
    cut = min(end, start + split)
    pieces = ((start, cut), (cut, end))
    assert _interval_covered((start, end), pieces)
