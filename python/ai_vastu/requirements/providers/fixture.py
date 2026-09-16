from __future__ import annotations

import re

from ai_vastu.requirements.models import (
    Direction,
    EvidenceSource,
    ProposedDirection,
    ProposedFloat,
    ProposedInt,
    RequirementDraft,
    RoomRequirementDraft,
    VastuMode,
)
from ai_vastu.requirements.providers.base import InterpretationInput

_DIMENSION_RE = re.compile(
    r"(?P<a>\d+(?:\.\d+)?)\s*(?:ft|feet|foot|')?\s*[x\u00d7]\s*"
    r"(?P<b>\d+(?:\.\d+)?)\s*(?P<unit>mm|cm|m|ft|feet|foot|')?",
    re.IGNORECASE,
)


def _to_mm(value: float, unit: str) -> int:
    normalized = unit.lower()
    if normalized in {"ft", "feet", "foot", "'", ""}:
        return round(value * 304.8)
    if normalized == "m":
        return round(value * 1000)
    if normalized == "cm":
        return round(value * 10)
    if normalized == "mm":
        return round(value)
    raise ValueError(f"Unsupported fixture unit: {unit}")


def _direction(text: str, phrase: str) -> Direction | None:
    patterns = {
        Direction.NE: ("north east", "northeast", "ne"),
        Direction.NW: ("north west", "northwest", "nw"),
        Direction.SE: ("south east", "southeast", "se"),
        Direction.SW: ("south west", "southwest", "sw"),
        Direction.N: ("north", "n"),
        Direction.E: ("east", "e"),
        Direction.S: ("south", "s"),
        Direction.W: ("west", "w"),
    }
    lowered = text.lower()
    for direction, names in patterns.items():
        for name in names:
            escaped_name = re.escape(name)

            direction_before_phrase = (
                rf"\b{escaped_name}\b[\s-]*{phrase}\b"
            )
            phrase_before_direction = (
                rf"\b{phrase}\b"
                rf"(?:\s+(?:on|to|at|towards?))?"
                rf"[\s:=-]*\b{escaped_name}\b"
            )

            if (
                re.search(direction_before_phrase, lowered)
                or re.search(phrase_before_direction, lowered)
            ):
                return direction

    return None


class FixtureRequirementsProvider:
    name = "fixture"

    def interpret(self, request: InterpretationInput) -> RequirementDraft:
        text = request.prompt
        lowered = text.lower()
        questions: list[str] = []
        warnings: list[str] = []
        rooms: list[RoomRequirementDraft] = []

        width = None
        depth = None
        match = _DIMENSION_RE.search(text)
        if match:
            unit = match.group("unit") or "ft"
            width = ProposedInt(
                value=_to_mm(float(match.group("a")), unit),
                source=EvidenceSource.PROMPT,
                confidence=0.98,
            )
            depth = ProposedInt(
                value=_to_mm(float(match.group("b")), unit),
                source=EvidenceSource.PROMPT,
                confidence=0.98,
            )
        else:
            questions.append("What are the exact plot width and depth?")

        road = _direction(text, "road")
        road_side = (
            ProposedDirection(
                value=road,
                source=EvidenceSource.PROMPT,
                confidence=0.96,
            )
            if road
            else None
        )
        if road_side is None:
            questions.append("Which plot boundary has road/access?")

        facing = _direction(text, "facing")
        entrance_facing = (
            ProposedDirection(
                value=facing,
                source=EvidenceSource.PROMPT,
                confidence=0.82,
            )
            if facing
            else None
        )
        if facing is not None and road is None:
            warnings.append(
                "A facing preference was detected, but it was not treated as the road side."
            )

        north_rotation = None
        north_match = re.search(
            r"(?:north|true north)[^\d]{0,20}(\d+(?:\.\d+)?)\s*(?:deg|°)",
            lowered,
        )
        if north_match:
            north_rotation = ProposedFloat(
                value=float(north_match.group(1)),
                source=EvidenceSource.PROMPT,
                confidence=0.97,
            )
        else:
            questions.append(
                "What is the true-North rotation in degrees? Use 0° if drawing +Y is North."
            )

        floor_count_value = 1
        g_plus = re.search(r"\bg\s*\+\s*(\d+)\b", lowered)
        if g_plus:
            floor_count_value = int(g_plus.group(1)) + 1
        elif "duplex" in lowered:
            floor_count_value = 2

        floor_count = ProposedInt(
            value=floor_count_value,
            source=EvidenceSource.PROMPT,
            confidence=0.84 if floor_count_value > 1 else 0.65,
        )

        bedroom_count_value = 0
        bhk = re.search(r"\b(\d+)\s*bhk\b", lowered)
        bedroom_word = re.search(r"\b(\d+)\s*bedrooms?\b", lowered)
        if bhk:
            bedroom_count_value = int(bhk.group(1))
        elif bedroom_word:
            bedroom_count_value = int(bedroom_word.group(1))

        bedroom_count = ProposedInt(
            value=bedroom_count_value,
            source=EvidenceSource.PROMPT,
            confidence=0.95 if bedroom_count_value else 0.45,
        )
        if bedroom_count_value:
            rooms.append(
                RoomRequirementDraft(
                    room_type="bedroom",
                    quantity=bedroom_count_value,
                    source=EvidenceSource.PROMPT,
                    confidence=0.95,
                )
            )

        keyword_rooms = {
            "kitchen": "kitchen",
            "puja": "puja",
            "pooja": "puja",
            "mandir": "puja",
            "home office": "home_office",
            "office": "home_office",
            "utility": "utility",
            "store": "store",
            "servant": "servant_room",
            "courtyard": "courtyard",
            "dining": "dining",
        }
        seen: set[str] = {item.room_type for item in rooms}
        for keyword, room_type in keyword_rooms.items():
            if keyword in lowered and room_type not in seen:
                rooms.append(
                    RoomRequirementDraft(
                        room_type=room_type,
                        source=EvidenceSource.PROMPT,
                        confidence=0.88,
                    )
                )
                seen.add(room_type)

        parking_count_value = 0
        car_match = re.search(r"\b(\d+)[-\s]*car\b", lowered)
        if car_match:
            parking_count_value = int(car_match.group(1))
        elif "parking" in lowered:
            parking_count_value = 1

        vastu_mode = VastuMode.STRICT if "strict vastu" in lowered else VastuMode.BALANCED

        if request.references:
            warnings.append(
                "Reference files were accepted but fixture mode does not visually interpret them."
            )

        return RequirementDraft(
            draft_id=request.draft_id,
            user_id=request.user_id,
            project_id=request.project_id,
            prompt=request.prompt,
            plot_width_mm=width,
            plot_depth_mm=depth,
            north_rotation_deg=north_rotation,
            road_side=road_side,
            entrance_facing=entrance_facing,
            floor_count=floor_count,
            bedroom_count=bedroom_count,
            parking_count=ProposedInt(
                value=parking_count_value,
                source=EvidenceSource.PROMPT,
                confidence=0.9 if parking_count_value else 0.5,
            ),
            vastu_mode=vastu_mode,
            rooms=rooms,
            questions=questions,
            warnings=warnings,
            reference_names=[item.filename for item in request.references],
            provider=self.name,
        )
