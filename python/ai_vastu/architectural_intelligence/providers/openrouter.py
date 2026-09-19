from __future__ import annotations

import json
from typing import Any

import httpx

from ai_vastu.openrouter_http import (
    OpenRouterClient,
    OpenRouterConfigurationError,
    OpenRouterModelPolicy,
    OpenRouterRequestError,
    schema_instruction,
)

from ..errors import (
    ArchitecturalIntelligenceConfigurationError,
    ArchitecturalIntelligenceProviderError,
)
from ..models import ArchitecturalDesignIntent
from .base import ArchitecturalReasoningInput

_SYSTEM = """You are the architectural reasoning layer for an Indian residential
planning system.

Act as a senior residential architect converting a confirmed client program into
STRUCTURED SOFT DESIGN INTENT for a deterministic solver.

Focus on functional zoning, entrance sequence, living-dining-kitchen
relationships, bedroom privacy, practical toilet access and visual privacy,
wardrobe/furniture needs stated by the client, daylight, ventilation,
service/plumbing clustering, short legible circulation, parking access, and
avoiding unusable leftover spaces.

When residential precedent studies are supplied:
- Treat them as REAL-PLAN TOPOLOGY EVIDENCE, not as authoritative designs.
- Similarity/retrieval scores indicate brief similarity only; they are NOT
  architectural-quality scores.
- Study recurring entry sequences, room connectivity, adjacency patterns,
  exterior exposure, area proportions, and circulation organization.
- Prefer relationships supported by multiple relevant precedents over an
  isolated precedent.
- Do NOT copy a precedent blindly.
- Do NOT copy precedent coordinates or exact dimensions.
- Adapt useful topology to the confirmed client brief, plot proportions,
  orientation, requested spaces, circulation needs, and other constraints.
- ResPlan's generic "bathroom" semantic does NOT establish whether a sanitary
  space is attached, common, bath-only, powder-room, or another subtype.
- ResPlan does NOT provide a puja semantic. Never reinterpret storage, balcony,
  or another room as puja merely to match a precedent.
- Never create a puja-sanitary adjacency from precedent evidence.
- If precedent evidence conflicts with confirmed requirements, confirmed
  requirements win.
- Use planning_notes or warnings when precedent evidence is ambiguous.

CRITICAL AUTHORITY BOUNDARY:
- Do NOT draw authoritative geometry.
- Do NOT output coordinates, walls, doors, polygons, or a finished floor plan.
- Do NOT invent exact room dimensions. preferred_* dimensions may be populated
  only when the client explicitly stated that dimension in the supplied brief
  or confirmed room notes.
- Do NOT create hard architectural constraints from your own judgement.
- Do NOT apply Vastu placement rules here. Vastu weighting is a separate soft layer.
- Safety, geometry validity, client-confirmed requirements and statutory constraints
  outrank your suggestions.
- Preserve ambiguity in warnings/planning_notes.
- Return JSON only.
"""


class OpenRouterArchitecturalIntelligenceProvider:
    name = "openrouter"

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
    def from_environment(cls) -> OpenRouterArchitecturalIntelligenceProvider:
        try:
            return cls(
                client=OpenRouterClient.from_environment(),
                policy=OpenRouterModelPolicy.from_environment(),
            )
        except OpenRouterConfigurationError as exc:
            raise ArchitecturalIntelligenceConfigurationError(str(exc)) from exc

    def reason(
        self,
        request: ArchitecturalReasoningInput,
    ) -> ArchitecturalDesignIntent:
        confirmed_json = json.dumps(
            request.confirmed.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        precedent_text = ""

        if request.precedent_context:
            precedent_json = json.dumps(
                request.precedent_context,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )

            precedent_text = (
                "\n\nRetrieved residential precedent studies:\n"
                + precedent_json
                + "\n\nUse the precedents as topology evidence only. "
                "Derive and adapt useful spatial patterns; do not copy "
                "geometry, dimensions, or unsupported semantics."
            )

        user_text = (
            "Original client brief:\n"
            + request.original_prompt
            + "\n\nHuman-confirmed planning requirements:\n"
            + confirmed_json
            + precedent_text
            + "\n\n"
            + schema_instruction(ArchitecturalDesignIntent.model_json_schema())
        )

        def validate(parsed: dict[str, Any], model: str) -> ArchitecturalDesignIntent:
            payload = dict(parsed)
            payload.update(
                {
                    "schema_version": "26A.1",
                    "project_id": str(request.confirmed.project_id),
                    "draft_id": str(request.confirmed.draft_id),
                    "provider": self.name,
                    "model": model,
                    "content_hash": None,
                }
            )
            return ArchitecturalDesignIntent.model_validate(payload).with_content_hash()

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_text},
                ),
                models=self._policy.reasoning_chain,
                validator=validate,
                temperature=0.2,
            )
        except OpenRouterRequestError as exc:
            raise ArchitecturalIntelligenceProviderError(
                f"OpenRouter architectural reasoning failed: {exc}"
            ) from exc


def build_openrouter_architectural_intelligence_for_test(
    *,
    api_key: str,
    transport: httpx.BaseTransport,
) -> OpenRouterArchitecturalIntelligenceProvider:
    return OpenRouterArchitecturalIntelligenceProvider(
        client=OpenRouterClient(api_key=api_key, transport=transport),
        policy=OpenRouterModelPolicy(),
    )
