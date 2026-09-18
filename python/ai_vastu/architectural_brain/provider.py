from __future__ import annotations

import json
import os
from typing import Any, Protocol
from uuid import UUID

import httpx

from ai_vastu.openrouter_http import (
    OpenRouterClient,
    OpenRouterConfigurationError,
    OpenRouterModelPolicy,
    OpenRouterRequestError,
    schema_instruction,
)

from .models import ArchitecturalConcept, RetrievedPrecedent
from .topology import build_fallback_concept


class ArchitecturalBrainProvider(Protocol):
    def propose(
        self,
        *,
        project_id: UUID,
        original_prompt: str,
        width_mm: int,
        depth_mm: int,
        bedroom_count: int,
        toilet_count: int,
        parking_count: int,
        room_types: tuple[str, ...],
        road_side: str | None,
        entrance_side: str | None,
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]: ...


class FixtureArchitecturalBrainProvider:
    def propose(
        self,
        *,
        project_id: UUID,
        original_prompt: str,
        width_mm: int,
        depth_mm: int,
        bedroom_count: int,
        toilet_count: int,
        parking_count: int,
        room_types: tuple[str, ...],
        road_side: str | None,
        entrance_side: str | None,
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]:
        del (
            original_prompt,
            width_mm,
            depth_mm,
            bedroom_count,
            toilet_count,
            parking_count,
            road_side,
            entrance_side,
        )
        return tuple(
            build_fallback_concept(
                project_id=project_id,
                room_types=room_types,
                precedents=precedents,
                ordinal=index,
            )
            for index in range(concept_count)
        )


def _precedent_evidence(
    precedents: tuple[RetrievedPrecedent, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "precedent_id": item.fingerprint.precedent_id,
            "similarity_basis_points": item.similarity_basis_points,
            "width_mm": item.fingerprint.width_mm,
            "depth_mm": item.fingerprint.depth_mm,
            "floor_area_mm2": item.fingerprint.floor_area_mm2,
            "bedroom_count": item.fingerprint.bedroom_count,
            "toilet_count": item.fingerprint.toilet_count,
            "parking_count": item.fingerprint.parking_count,
            "room_types": item.fingerprint.room_types,
            "road_side": item.fingerprint.road_side,
            "entrance_side": item.fingerprint.entrance_side,
            "topology": [
                edge.model_dump(mode="json") for edge in item.fingerprint.topology
            ],
        }
        for item in precedents[:12]
    ]


def _brain_prompt(
    *,
    project_id: UUID,
    original_prompt: str,
    width_mm: int,
    depth_mm: int,
    bedroom_count: int,
    toilet_count: int,
    parking_count: int,
    room_types: tuple[str, ...],
    road_side: str | None,
    entrance_side: str | None,
    precedents: tuple[RetrievedPrecedent, ...],
    concept_count: int,
) -> dict[str, Any]:
    return {
        "task": (
            "Act as a senior residential architect. Produce structured topology and "
            "room-sizing concepts only; never CAD coordinates. Treat the full confirmed "
            "site as valuable client property: every part of the site must have an "
            "intentional role in the eventual site-accounting layer, but do not assume "
            "every square millimetre may legally be roofed. Build a coherent residential "
            "access graph before geometry. Parking must connect to the road and must not "
            "be oversized as filler. Keep service spaces compact, protect bedroom privacy, "
            "cluster kitchen/dining logically, provide short legible circulation, preserve "
            "daylight/ventilation opportunity, and avoid isolated rooms or accidental "
            "residual strips. Use retrieved precedents as evidence, not as geometry to copy."
        ),
        "authority_boundary": (
            "The model supplies soft architectural concept intent only. The deterministic "
            "OR-Tools/CAD pipeline remains authoritative for exact integer-millimetre geometry."
        ),
        "project_id": str(project_id),
        "client_request": original_prompt,
        "confirmed_site": {
            "width_mm": width_mm,
            "depth_mm": depth_mm,
            "site_area_mm2": width_mm * depth_mm,
            "road_side": road_side,
            "entrance_side": entrance_side,
        },
        "confirmed_program": {
            "bedroom_count": bedroom_count,
            "toilet_count": toilet_count,
            "parking_count": parking_count,
            "room_types": room_types,
        },
        "retrieved_precedents": _precedent_evidence(precedents),
        "concept_count": concept_count,
    }


class GeminiArchitecturalBrainProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    @classmethod
    def from_environment(cls) -> GeminiArchitecturalBrainProvider:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY is required for the architectural brain.")
        model = os.getenv(
            "AI_VASTU_ARCHITECTURAL_BRAIN_MODEL",
            "gemini-3.1-flash-lite",
        ).strip()
        return cls(api_key=key, model=model)

    def propose(
        self,
        *,
        project_id: UUID,
        original_prompt: str,
        width_mm: int,
        depth_mm: int,
        bedroom_count: int,
        toilet_count: int,
        parking_count: int,
        room_types: tuple[str, ...],
        road_side: str | None,
        entrance_side: str | None,
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]:
        prompt = _brain_prompt(
            project_id=project_id,
            original_prompt=original_prompt,
            width_mm=width_mm,
            depth_mm=depth_mm,
            bedroom_count=bedroom_count,
            toilet_count=toilet_count,
            parking_count=parking_count,
            room_types=room_types,
            road_side=road_side,
            entrance_side=entrance_side,
            precedents=precedents,
            concept_count=concept_count,
        )
        response = httpx.post(
            (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self._model}:generateContent"
            ),
            params={"key": self._api_key},
            json={
                "contents": [{"parts": [{"text": json.dumps(prompt)}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.3,
                },
            },
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw)
        results: list[ArchitecturalConcept] = []
        for item in parsed.get("concepts", []):
            if not isinstance(item, dict):
                continue
            item.update(
                {
                    "schema_version": "26.4B.1",
                    "project_id": str(project_id),
                    "precedent_ids": [p.fingerprint.precedent_id for p in precedents[:8]],
                    "authoritative_geometry": False,
                    "content_hash": None,
                }
            )
            results.append(ArchitecturalConcept.model_validate(item).with_content_hash())
        if not results:
            return FixtureArchitecturalBrainProvider().propose(
                project_id=project_id,
                original_prompt=original_prompt,
                width_mm=width_mm,
                depth_mm=depth_mm,
                bedroom_count=bedroom_count,
                toilet_count=toilet_count,
                parking_count=parking_count,
                room_types=room_types,
                road_side=road_side,
                entrance_side=entrance_side,
                precedents=precedents,
                concept_count=concept_count,
            )
        return tuple(results[:concept_count])


class OpenRouterArchitecturalBrainProvider:
    def __init__(
        self,
        *,
        client: OpenRouterClient,
        policy: OpenRouterModelPolicy,
    ) -> None:
        policy.validate()
        self._client = client
        self._policy = policy

    @classmethod
    def from_environment(cls) -> OpenRouterArchitecturalBrainProvider:
        try:
            return cls(
                client=OpenRouterClient.from_environment(),
                policy=OpenRouterModelPolicy.from_environment(),
            )
        except OpenRouterConfigurationError as exc:
            raise RuntimeError(str(exc)) from exc

    def propose(
        self,
        *,
        project_id: UUID,
        original_prompt: str,
        width_mm: int,
        depth_mm: int,
        bedroom_count: int,
        toilet_count: int,
        parking_count: int,
        room_types: tuple[str, ...],
        road_side: str | None,
        entrance_side: str | None,
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]:
        prompt = _brain_prompt(
            project_id=project_id,
            original_prompt=original_prompt,
            width_mm=width_mm,
            depth_mm=depth_mm,
            bedroom_count=bedroom_count,
            toilet_count=toilet_count,
            parking_count=parking_count,
            room_types=room_types,
            road_side=road_side,
            entrance_side=entrance_side,
            precedents=precedents,
            concept_count=concept_count,
        )
        prompt["output_contract"] = (
            "Return an object with key 'concepts'. Each array item must validate as an "
            "ArchitecturalConcept. "
            + schema_instruction(ArchitecturalConcept.model_json_schema())
        )

        def validate(
            parsed: dict[str, Any],
            _model: str,
        ) -> tuple[ArchitecturalConcept, ...]:
            raw_concepts = parsed.get("concepts")
            if not isinstance(raw_concepts, list) or not raw_concepts:
                raise ValueError("Architectural Brain returned no concepts.")

            concepts: list[ArchitecturalConcept] = []
            for raw in raw_concepts[:concept_count]:
                if not isinstance(raw, dict):
                    raise ValueError("Architectural Brain concept was not an object.")
                item = dict(raw)
                item.update(
                    {
                        "schema_version": "26.4B.1",
                        "project_id": str(project_id),
                        "precedent_ids": [
                            item.fingerprint.precedent_id for item in precedents[:8]
                        ],
                        "authoritative_geometry": False,
                        "content_hash": None,
                    }
                )
                concepts.append(
                    ArchitecturalConcept.model_validate(item).with_content_hash()
                )
            if not concepts:
                raise ValueError("Architectural Brain returned no valid concepts.")
            return tuple(concepts)

        try:
            return self._client.complete_validated_json(
                messages=(
                    {
                        "role": "system",
                        "content": (
                            "You are the primary human-like architectural planning brain "
                            "for Indian residential layouts. Think in topology, zoning, "
                            "access, room proportion and site use before coordinates. "
                            "Never emit authoritative CAD geometry. Return JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            prompt,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ),
                    },
                ),
                models=self._policy.reasoning_chain,
                validator=validate,
                temperature=0.3,
            )
        except OpenRouterRequestError as exc:
            raise RuntimeError(f"OpenRouter Architectural Brain failed: {exc}") from exc


def create_architectural_brain_provider() -> ArchitecturalBrainProvider:
    name = os.getenv("AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER", "fixture").strip().lower()
    if name in {"fixture", "deterministic"}:
        return FixtureArchitecturalBrainProvider()
    if name == "gemini":
        return GeminiArchitecturalBrainProvider.from_environment()
    if name == "openrouter":
        return OpenRouterArchitecturalBrainProvider.from_environment()
    raise RuntimeError(
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER must be "
        "fixture/deterministic/gemini/openrouter."
    )
