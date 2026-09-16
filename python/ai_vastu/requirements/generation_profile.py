from __future__ import annotations

from dataclasses import dataclass

PROFILE_VERSION = "24B.1"


@dataclass(frozen=True, slots=True)
class RoomMinimum:
    min_width_mm: int
    min_depth_mm: int
    min_area_mm2: int


ROOM_MINIMUMS: dict[str, RoomMinimum] = {
    "living": RoomMinimum(3000, 3600, 10_800_000),
    "drawing": RoomMinimum(3000, 3300, 9_900_000),
    "dining": RoomMinimum(2700, 3000, 8_100_000),
    "kitchen": RoomMinimum(2400, 2400, 5_760_000),
    "utility": RoomMinimum(1500, 1800, 2_700_000),
    "pantry": RoomMinimum(1200, 1500, 1_800_000),
    "store": RoomMinimum(1200, 1500, 1_800_000),
    "puja": RoomMinimum(1200, 1200, 1_440_000),
    "master_bedroom": RoomMinimum(3300, 3600, 11_880_000),
    "bedroom": RoomMinimum(3000, 3000, 9_000_000),
    "parents_bedroom": RoomMinimum(3000, 3300, 9_900_000),
    "guest_bedroom": RoomMinimum(3000, 3000, 9_000_000),
    "children_bedroom": RoomMinimum(2700, 3000, 8_100_000),
    "attached_toilet": RoomMinimum(1200, 2100, 2_520_000),
    "common_toilet": RoomMinimum(1200, 1800, 2_160_000),
    "powder_room": RoomMinimum(1000, 1500, 1_500_000),
    "bath": RoomMinimum(1200, 1800, 2_160_000),
    "dressing": RoomMinimum(1500, 1800, 2_700_000),
    "wardrobe": RoomMinimum(1200, 1500, 1_800_000),
    "staircase": RoomMinimum(1800, 3000, 5_400_000),
    "lift": RoomMinimum(1500, 1500, 2_250_000),
    "lobby": RoomMinimum(1500, 1800, 2_700_000),
    "corridor": RoomMinimum(1000, 1800, 1_800_000),
    "foyer": RoomMinimum(1500, 1800, 2_700_000),
    "verandah": RoomMinimum(1500, 2400, 3_600_000),
    "balcony": RoomMinimum(1200, 2400, 2_880_000),
    "terrace": RoomMinimum(2400, 2400, 5_760_000),
    "courtyard": RoomMinimum(2400, 2400, 5_760_000),
    "parking": RoomMinimum(2500, 5000, 12_500_000),
    "garage": RoomMinimum(3000, 5500, 16_500_000),
    "home_office": RoomMinimum(2400, 2700, 6_480_000),
    "servant_room": RoomMinimum(2400, 2700, 6_480_000),
    "servant_toilet": RoomMinimum(1000, 1500, 1_500_000),
    "laundry": RoomMinimum(1500, 1800, 2_700_000),
    "study": RoomMinimum(2100, 2400, 5_040_000),
    "family_lounge": RoomMinimum(2700, 3000, 8_100_000),
}

ROOM_ALIASES: dict[str, str] = {
    "master bedroom": "master_bedroom",
    "parents bedroom": "parents_bedroom",
    "guest bedroom": "guest_bedroom",
    "children bedroom": "children_bedroom",
    "child bedroom": "children_bedroom",
    "attached toilet": "attached_toilet",
    "common toilet": "common_toilet",
    "powder room": "powder_room",
    "home office": "home_office",
    "servant room": "servant_room",
    "servant toilet": "servant_toilet",
    "family lounge": "family_lounge",
    "pooja": "puja",
    "mandir": "puja",
}


def normalize_room_type(value: str) -> str:
    normalized = " ".join(value.strip().lower().replace("-", " ").split())
    return ROOM_ALIASES.get(normalized, normalized.replace(" ", "_"))
