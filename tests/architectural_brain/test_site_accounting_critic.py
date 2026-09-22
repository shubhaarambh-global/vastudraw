from tests.exporting.helpers import export_plan, rectangle

from ai_vastu.architectural_brain.critic import critique_plan
from ai_vastu.plan_schema import RoomType


def _finding_codes(document: object) -> set[str]:
    critique = critique_plan(document)  # type: ignore[arg-type]
    return {finding.code for finding in critique.findings}


def test_fully_accounted_canonical_plan_has_no_residual_rejection() -> None:
    document = export_plan()

    critique = critique_plan(document)
    codes = {finding.code for finding in critique.findings}

    assert "UNEXPLAINED_SITE_RESIDUAL" not in codes
    assert critique.accepted


def test_ninety_percent_room_coverage_is_still_rejected_when_blank() -> None:
    document = export_plan()

    floor = document.floors[0]
    living, kitchen = floor.rooms

    # Preserve 90% room-envelope occupancy:
    #
    # living  = 5000 * 8000 = 40 m2
    # kitchen = 4000 * 8000 = 32 m2
    # total   = 72 m2 / 80 m2 = 90%
    #
    # The remaining 1000 * 8000 strip is genuine unclassified
    # geometry. The old 85% site-allocation threshold would accept
    # the percentage, but geometric accounting must reject it.
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

    bad_floor = floor.model_copy(
        update={
            "rooms": (
                living,
                smaller_kitchen,
            )
        }
    )

    bad_document = document.model_copy(
        update={
            "floors": (bad_floor,),
            "content_hash": None,
        }
    ).with_content_hash()

    critique = critique_plan(bad_document)
    codes = {finding.code for finding in critique.findings}

    assert "LOW_SITE_ALLOCATION" not in codes
    assert "UNEXPLAINED_SITE_RESIDUAL" in codes
    assert not critique.accepted

    residual = next(
        finding for finding in critique.findings if finding.code == "UNEXPLAINED_SITE_RESIDUAL"
    )

    assert "8.00 m2" in residual.message
    assert "10.0%" in residual.message
    assert "bbox=(9000, 0)-(10000, 8000) mm" in residual.message


def test_parking_area_has_no_universal_hard_maximum() -> None:
    document = export_plan()
    floor = document.floors[0]
    living, kitchen = floor.rooms

    large_parking = living.model_copy(
        update={
            "room_type": RoomType.PARKING,
            "name": "Parking",
        }
    )
    updated_floor = floor.model_copy(
        update={
            "rooms": (large_parking, kitchen),
        }
    )
    updated_document = document.model_copy(
        update={
            "floors": (updated_floor,),
            "content_hash": None,
        }
    ).with_content_hash()

    critique = critique_plan(updated_document)
    codes = {finding.code for finding in critique.findings}

    assert "OVERSIZED_PARKING" not in codes
    assert critique.accepted
