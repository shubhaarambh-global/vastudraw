from uuid import UUID

import pytest
from tests.exporting.helpers import (
    export_plan,
    rectangle,
)

from ai_vastu.architectural_brain.critic import (
    critique_plan,
)
from ai_vastu.architectural_brain.site_accounting import (
    analyze_floor_site_accounting,
)
from ai_vastu.plan_schema import (
    PurposefulSiteSpace,
    SiteSpaceKind,
    SiteSpaceSource,
)

SITE_SPACE_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _plan_with_site_space(
    *,
    site_polygon,
):
    document = export_plan()
    floor = document.floors[0]
    living, kitchen = floor.rooms

    # Existing export fixture covers a 10 m x 8 m envelope
    # with two 5 m-wide rooms. Shrink the kitchen to 4 m,
    # deliberately leaving a 1 m x 8 m strip.
    smaller_kitchen = kitchen.model_copy(
        update={
            "polygon": rectangle(
                5_000,
                0,
                9_000,
                8_000,
            )
        }
    )

    site_space = PurposefulSiteSpace(
        id=SITE_SPACE_ID,
        kind=SiteSpaceKind.OPEN_SPACE,
        polygon=site_polygon,
        label="Purposeful open-to-sky strip",
        source=SiteSpaceSource.SYSTEM_DERIVED,
    )

    floor = floor.model_copy(
        update={
            "rooms": (
                living,
                smaller_kitchen,
            ),
            "site_spaces": (site_space,),
        }
    )

    return document.model_copy(
        update={
            "floors": (floor,),
            "content_hash": None,
        }
    ).with_content_hash()


def test_explicit_purposeful_space_closes_site_accounting() -> None:
    document = _plan_with_site_space(
        site_polygon=rectangle(
            9_000,
            0,
            10_000,
            8_000,
        )
    )

    analysis = analyze_floor_site_accounting(
        envelope=document.buildable_area.polygon,
        floor=document.floors[0],
        solver_step_mm=1,
    )

    assert analysis.accounting.allocation_basis_points == 10_000
    assert analysis.accounting.residual_area_mm2 == 0
    assert analysis.unexplained_residual_area_mm2 == 0

    categories = {allocation.category for allocation in analysis.accounting.allocations}

    assert "OPEN_SPACE" in categories

    critique = critique_plan(document)
    codes = {finding.code for finding in critique.findings}

    assert "LOW_SITE_ALLOCATION" not in codes
    assert "UNEXPLAINED_SITE_RESIDUAL" not in codes
    assert "INVALID_SITE_ACCOUNTING_GEOMETRY" not in codes


def test_purposeful_space_cannot_overlap_room_geometry() -> None:
    document = _plan_with_site_space(
        site_polygon=rectangle(
            8_000,
            0,
            10_000,
            8_000,
        )
    )

    with pytest.raises(
        ValueError,
        match="classified polygons overlap",
    ):
        analyze_floor_site_accounting(
            envelope=document.buildable_area.polygon,
            floor=document.floors[0],
            solver_step_mm=1,
        )

    critique = critique_plan(document)

    assert not critique.accepted
    assert {finding.code for finding in critique.findings} == {"INVALID_SITE_ACCOUNTING_GEOMETRY"}


def test_purposeful_space_must_remain_inside_buildable_envelope() -> None:
    document = _plan_with_site_space(
        site_polygon=rectangle(
            9_000,
            0,
            11_000,
            8_000,
        )
    )

    critique = critique_plan(document)

    assert not critique.accepted
    assert {finding.code for finding in critique.findings} == {"INVALID_SITE_ACCOUNTING_GEOMETRY"}


def test_unclassified_residual_remains_rejected() -> None:
    document = export_plan()
    floor = document.floors[0]
    living, kitchen = floor.rooms

    smaller_kitchen = kitchen.model_copy(
        update={
            "polygon": rectangle(
                5_000,
                0,
                9_000,
                8_000,
            )
        }
    )

    floor = floor.model_copy(
        update={
            "rooms": (
                living,
                smaller_kitchen,
            ),
            "site_spaces": (),
        }
    )

    document = document.model_copy(
        update={
            "floors": (floor,),
            "content_hash": None,
        }
    ).with_content_hash()

    critique = critique_plan(document)

    codes = {finding.code for finding in critique.findings}

    assert "UNEXPLAINED_SITE_RESIDUAL" in codes
