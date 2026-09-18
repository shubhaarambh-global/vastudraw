from __future__ import annotations

import json
import os
from typing import Protocol
from uuid import UUID

import httpx

from .models import ArchitecturalConcept, RetrievedPrecedent
from .topology import build_fallback_concept


class ArchitecturalBrainProvider(Protocol):
    def propose(
        self,
        *,
        project_id: UUID,
        original_prompt: str,
        room_types: tuple[str, ...],
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]: ...


class FixtureArchitecturalBrainProvider:
    def propose(
        self,
        *,
        project_id: UUID,
        original_prompt: str,
        room_types: tuple[str, ...],
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]:
        del original_prompt
        return tuple(
            build_fallback_concept(
                project_id=project_id,
                room_types=room_types,
                precedents=precedents,
                ordinal=index,
            )
            for index in range(concept_count)
        )


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
        room_types: tuple[str, ...],
        precedents: tuple[RetrievedPrecedent, ...],
        concept_count: int,
    ) -> tuple[ArchitecturalConcept, ...]:
        evidence = [
            {
                "precedent_id": item.fingerprint.precedent_id,
                "similarity_basis_points": item.similarity_basis_points,
                "width_mm": item.fingerprint.width_mm,
                "depth_mm": item.fingerprint.depth_mm,
                "room_types": item.fingerprint.room_types,
                "topology": [edge.model_dump(mode="json") for edge in item.fingerprint.topology],
            }
            for item in precedents[:12]
        ]
        prompt = {
            "task": (
                "Act as a residential architect. Produce structured topology concepts only. "
                "Do not produce coordinates. Every room must participate in a coherent access "
                "graph. Parking must not be oversized as filler. Preserve practical circulation, "
                "privacy, external-wall opportunity and service logic."
            ),
            "project_id": str(project_id),
            "client_request": original_prompt,
            "room_types": room_types,
            "retrieved_precedents": evidence,
            "concept_count": concept_count,
        }
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
            item.update(
                {
                    "schema_version": "26.4B.1",
                    "project_id": str(project_id),
                    "precedent_ids": [p.fingerprint.precedent_id for p in precedents[:8]],
                    "authoritative_geometry": False,
                }
            )
            results.append(ArchitecturalConcept.model_validate(item).with_content_hash())
        if not results:
            return FixtureArchitecturalBrainProvider().propose(
                project_id=project_id,
                original_prompt=original_prompt,
                room_types=room_types,
                precedents=precedents,
                concept_count=concept_count,
            )
        return tuple(results[:concept_count])


def create_architectural_brain_provider() -> ArchitecturalBrainProvider:
    name = os.getenv("AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER", "fixture").strip().lower()
    if name in {"fixture", "deterministic"}:
        return FixtureArchitecturalBrainProvider()
    if name == "gemini":
        return GeminiArchitecturalBrainProvider.from_environment()
    raise RuntimeError(
        "AI_VASTU_ARCHITECTURAL_BRAIN_PROVIDER must be fixture/deterministic/gemini."
    )
