from ai_vastu.requirements.generation_profile import (
    PROFILE_VERSION,
    ROOM_MINIMUMS,
    normalize_room_type,
)


def test_generation_profile_version_is_24b_3() -> None:
    assert PROFILE_VERSION == "24B.3"


def test_live_natural_room_labels_resolve_to_supported_profiles() -> None:
    aliases = {
        "living room": "living",
        "living area": "living",
        "drawing room": "drawing",
        "dining room": "dining",
        "dining area": "dining",
        "puja room": "puja",
        "pooja room": "puja",
        "prayer room": "puja",
        "common toilet/bath": "common_toilet",
        "common toilet bath": "common_toilet",
        "common bathroom": "common_toilet",
        "car parking": "parking",
        "car park": "parking",
        "parking space": "parking",
        "utility room": "utility",
        "store room": "store",
        "study room": "study",
        "laundry room": "laundry",
    }

    for source, expected in aliases.items():
        actual = normalize_room_type(source)

        assert actual == expected
        assert actual in ROOM_MINIMUMS


def test_exact_canonical_room_types_remain_stable() -> None:
    for canonical in ROOM_MINIMUMS:
        assert normalize_room_type(canonical) == canonical


def test_current_live_brief_room_labels_are_all_supported() -> None:
    room_labels = (
        "bedroom",
        "kitchen",
        "living room",
        "dining area",
        "puja room",
        "common toilet/bath",
    )

    normalized = tuple(normalize_room_type(value) for value in room_labels)

    assert normalized == (
        "bedroom",
        "kitchen",
        "living",
        "dining",
        "puja",
        "common_toilet",
    )

    assert all(room_type in ROOM_MINIMUMS for room_type in normalized)
