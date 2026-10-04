from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import httpx

from ai_vastu.apinex_http import ApinexClient, ApinexConfigurationError
from ai_vastu.provider_runtime import ProviderRuntimeError
from ai_vastu.requirements.errors import RequirementsProviderError
from ai_vastu.requirements.models import EvidenceSource, RequirementDraft
from ai_vastu.requirements.providers.base import InterpretationInput


class ApinexRequirementsConfigurationError(RuntimeError):
    pass


_SYSTEM = """You are the requirements interpreter for an Indian residential
architectural planning system.

Extract planning requirements from the user's text. Reference filenames are
context only; do not claim to have inspected reference file contents in this
text-only adapter. Plan images and rendered PDF pages use the separate plan
recognition adapter.

CRITICAL BOUNDARY:
- You do not draw or modify authoritative geometry.
- You do not invent missing exact dimensions.
- Every proposed value remains confirmation-required.
- Inferences must use source=model_inference and require confirmation.
- Do not assume property-facing direction equals road side.
- Do not assume road side equals true North.
- Populate every corresponding field explicitly stated in the brief.
- Explicit text evidence uses source=prompt but still requires confirmation.
- Preserve ambiguity in questions/warnings.
"""


class ApinexRequirementsProvider:
    name = "apinex"

    def __init__(self, *, client: ApinexClient) -> None:
        self._client = client

    @classmethod
    def from_environment(cls) -> ApinexRequirementsProvider:
        try:
            return cls(client=ApinexClient.from_environment())
        except ApinexConfigurationError as exc:
            raise ApinexRequirementsConfigurationError(
                "APINEX requirements provider is not configured."
            ) from exc

    def interpret(self, request: InterpretationInput) -> RequirementDraft:
        reference_names = [item.filename for item in request.references]
        user_text = (
            "Project ID: "
            + str(request.project_id)
            + "\n\nClient brief:\n"
            + request.prompt
        )
        if reference_names:
            user_text += (
                "\n\nAttached reference filenames (contents are not available "
                "to this text adapter):\n"
                + "\n".join(reference_names)
            )
        user_text += (
            "\n\nExtract every explicitly stated dimension, count, direction, and room. "
            "Each proposed value must include value, source, confidence, and "
            "requires_confirmation."
        )

        def validate(parsed: dict[str, Any], model: str) -> RequirementDraft:
            payload = deepcopy(parsed)
            proposed_names = (
                "plot_width_mm",
                "plot_depth_mm",
                "north_rotation_deg",
                "road_side",
                "entrance_facing",
                "floor_count",
                "bedroom_count",
                "parking_count",
            )
            for name in proposed_names:
                proposed = payload.get(name)
                if not isinstance(proposed, dict):
                    continue
                proposed["requires_confirmation"] = True
                if proposed.get("source") == EvidenceSource.USER_CONFIRMED.value:
                    proposed["source"] = EvidenceSource.MODEL_INFERENCE.value
            rooms = payload.get("rooms")
            if isinstance(rooms, list):
                for room in rooms:
                    if (
                        isinstance(room, dict)
                        and room.get("source") == EvidenceSource.USER_CONFIRMED.value
                    ):
                        room["source"] = EvidenceSource.MODEL_INFERENCE.value
            payload.update(
                {
                    "schema_version": "24A.1",
                    "draft_id": str(request.draft_id),
                    "user_id": str(request.user_id),
                    "project_id": str(request.project_id),
                    "prompt": request.prompt,
                    "reference_names": reference_names,
                    "provider": self.name,
                    "model": model,
                }
            )
            return RequirementDraft.model_validate_json(json.dumps(payload))

        try:
            return self._client.complete_validated_json(
                messages=(
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_text},
                ),
                schema=RequirementDraft.model_json_schema(),
                validator=validate,
            )
        except ProviderRuntimeError as exc:
            raise RequirementsProviderError(exc.category) from exc


def build_apinex_requirements_provider_for_test(
    *, api_key: str, transport: httpx.BaseTransport
) -> ApinexRequirementsProvider:
    return ApinexRequirementsProvider(
        client=ApinexClient(api_key=api_key, transport=transport)
    )
