from __future__ import annotations

import json
import os
import re
from uuid import UUID

import httpx

from ai_vastu.plan_schema import AdjacencyPreference, AdjacencyProhibition, RoomType
from ai_vastu.requirements.generation_adapter import CompiledGeneration

from .models import RevisionDirective, RevisionOperation, StructuredRevisionIntent

_FT_TO_MM = 304.8


def _normalize_room_type(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def deterministic_revision_interpretation(
    *,
    project_id: UUID,
    base_revision_id: UUID,
    request: str,
) -> StructuredRevisionIntent:
    text = request.lower()
    directives: list[RevisionDirective] = []
    room_tokens = (
        "living",
        "dining",
        "kitchen",
        "bedroom",
        "master bedroom",
        "puja",
        "parking",
        "lobby",
        "common toilet",
        "utility",
        "store",
    )
    room = next((token for token in room_tokens if token in text), None)
    delta_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ft|feet|foot)", text)
    if room and delta_match:
        delta = round(float(delta_match.group(1)) * _FT_TO_MM)
        if any(token in text for token in ("wider", "increase width", "more wide")):
            directives.append(
                RevisionDirective(
                    operation=RevisionOperation.INCREASE_DIMENSION,
                    room_type=_normalize_room_type(room),
                    axis="WIDTH",
                    delta_mm=delta,
                )
            )
        elif any(token in text for token in ("deeper", "increase depth", "longer")):
            directives.append(
                RevisionDirective(
                    operation=RevisionOperation.INCREASE_DIMENSION,
                    room_type=_normalize_room_type(room),
                    axis="DEPTH",
                    delta_mm=delta,
                )
            )
        elif any(token in text for token in ("bigger", "increase", "larger")):
            directives.append(
                RevisionDirective(
                    operation=RevisionOperation.INCREASE_AREA,
                    room_type=_normalize_room_type(room),
                    delta_mm=delta,
                )
            )
    return StructuredRevisionIntent(
        project_id=project_id,
        base_revision_id=base_revision_id,
        original_request=request,
        directives=tuple(directives),
    )


def interpret_revision_with_gemini(
    *,
    project_id: UUID,
    base_revision_id: UUID,
    request: str,
) -> StructuredRevisionIntent:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return deterministic_revision_interpretation(
            project_id=project_id,
            base_revision_id=base_revision_id,
            request=request,
        )
    model = os.getenv("AI_VASTU_REVISION_MODEL", "gemini-3.1-flash-lite").strip()
    prompt = {
        "task": (
            "Convert a residential-plan revision request to structured intent only. "
            "Never output CAD coordinates. Preserve all unmentioned requirements."
        ),
        "project_id": str(project_id),
        "base_revision_id": str(base_revision_id),
        "request": request,
        "operations": [item.value for item in RevisionOperation],
        "units": "millimetres",
    }
    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json={
            "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1},
        },
        timeout=60,
    )
    response.raise_for_status()
    raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    payload = json.loads(raw)
    payload.update(
        {
            "schema_version": "26D.1",
            "project_id": str(project_id),
            "base_revision_id": str(base_revision_id),
            "original_request": request,
            "preserve_unmentioned_requirements": True,
            "authoritative_geometry": False,
        }
    )
    return StructuredRevisionIntent.model_validate(payload)


def _room_type(value: str) -> RoomType | None:
    aliases = {"master_bedroom": "bedroom", "toilet": "common_toilet"}
    normalized = aliases.get(_normalize_room_type(value), _normalize_room_type(value))
    try:
        return RoomType(normalized)
    except ValueError:
        return None


def apply_revision_intent(
    compiled: CompiledGeneration,
    intent: StructuredRevisionIntent,
) -> CompiledGeneration:
    updated = []
    notices = list(compiled.notices)
    for requirement in compiled.request.room_requirements:
        changes: dict[str, object] = {}
        for directive in intent.directives:
            if _room_type(directive.room_type) != requirement.room_type:
                continue
            if directive.operation is RevisionOperation.INCREASE_DIMENSION and directive.delta_mm:
                if directive.axis == "WIDTH":
                    base = requirement.preferred_width_mm or requirement.min_width_mm
                    target = base + directive.delta_mm
                    if requirement.max_width_mm is not None:
                        target = min(target, requirement.max_width_mm)
                    changes["preferred_width_mm"] = target
                elif directive.axis == "DEPTH":
                    base = requirement.preferred_depth_mm or requirement.min_depth_mm
                    target = base + directive.delta_mm
                    if requirement.max_depth_mm is not None:
                        target = min(target, requirement.max_depth_mm)
                    changes["preferred_depth_mm"] = target
            elif directive.operation is RevisionOperation.PREFER_ADJACENCY:
                related = _room_type(directive.related_room_type or "")
                if related is not None:
                    changes["adjacency_preferences"] = (
                        *requirement.adjacency_preferences,
                        AdjacencyPreference(
                            target_room_type=related,
                            weight=95,
                            max_gap_mm=300,
                            min_shared_length_mm=800,
                        ),
                    )
            elif directive.operation is RevisionOperation.AVOID_ADJACENCY:
                related = _room_type(directive.related_room_type or "")
                if related is not None:
                    changes["adjacency_prohibitions"] = (
                        *requirement.adjacency_prohibitions,
                        AdjacencyProhibition(target_room_type=related, hard=False),
                    )
        updated.append(requirement.model_copy(update=changes))

    notices.append(
        "Phase 26D revision intent applied as preferences; exact geometry remains deterministic."
    )
    request = compiled.request.model_copy(update={"room_requirements": tuple(updated)})
    return CompiledGeneration(
        request=request,
        profile_version=compiled.profile_version,
        notices=tuple(notices),
    )
