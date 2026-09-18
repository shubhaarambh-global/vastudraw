from __future__ import annotations

import os

from ai_vastu.requirements.generation_profile import normalize_room_type
from ai_vastu.requirements.models import ConfirmedRequirements

from .catalog import load_soft_vastu_catalog
from .errors import (
    VastuReasoningConfigurationError,
    VastuReasoningProviderError,
)
from .models import (
    RuleApplicability,
    VastuInfluenceMode,
    VastuReasoningProfile,
    VastuRuleReasoning,
)
from .providers import (
    FixtureVastuReasoningProvider,
    GeminiVastuReasoningProvider,
    OpenAIVastuReasoningProvider,
    OpenRouterVastuReasoningProvider,
    VastuReasoningInput,
    VastuReasoningProvider,
)

_MODE_WEIGHTS: dict[VastuInfluenceMode, tuple[int, int]] = {
    VastuInfluenceMode.PRACTICAL: (7000, 3000),
    VastuInfluenceMode.BALANCED: (5000, 5000),
    VastuInfluenceMode.VASTU_FORWARD: (3000, 7000),
}


def configured_provider_name() -> str:
    return os.getenv("AI_VASTU_VASTU_PROVIDER", "disabled").strip().lower()


def vastu_reasoning_enabled() -> bool:
    return configured_provider_name() not in {"", "disabled", "off", "none"}


def create_vastu_reasoning_provider() -> VastuReasoningProvider:
    name = configured_provider_name()
    if name == "fixture":
        return FixtureVastuReasoningProvider()
    if name == "gemini":
        return GeminiVastuReasoningProvider.from_environment()
    if name == "openai":
        return OpenAIVastuReasoningProvider.from_environment()
    if name == "openrouter":
        return OpenRouterVastuReasoningProvider.from_environment()
    raise VastuReasoningConfigurationError(
        "Unsupported AI_VASTU_VASTU_PROVIDER: "
        f"{name or '<blank>'}. Use disabled, fixture, gemini, openai, or openrouter."
    )


def influence_mode_for_confirmed(
    confirmed: ConfirmedRequirements,
) -> VastuInfluenceMode:
    override = os.getenv("AI_VASTU_VASTU_INFLUENCE_MODE", "").strip().lower()
    if override:
        try:
            return VastuInfluenceMode(override)
        except ValueError as exc:
            raise VastuReasoningConfigurationError(
                "AI_VASTU_VASTU_INFLUENCE_MODE must be practical, balanced, or vastu_forward."
            ) from exc

    legacy = confirmed.vastu_mode.value
    if legacy == "space_efficient":
        return VastuInfluenceMode.PRACTICAL
    if legacy == "strict":
        return VastuInfluenceMode.VASTU_FORWARD
    return VastuInfluenceMode.BALANCED


def _normalize_profile(
    raw: VastuReasoningProfile,
    request: VastuReasoningInput,
) -> VastuReasoningProfile:
    catalog = request.catalog
    rules_by_id = {rule.rule_id: rule for rule in catalog.rules}
    raw_by_id = {rule.rule_id: rule for rule in raw.rules}

    unknown = sorted(set(raw_by_id) - set(rules_by_id))
    if unknown:
        raise VastuReasoningProviderError(f"Vastu reasoning returned unknown rule IDs: {unknown}")

    present_room_types = {normalize_room_type(room.room_type) for room in request.confirmed.rooms}

    if request.confirmed.bedroom_count > 0:
        present_room_types.add("bedroom")

    if request.confirmed.parking_count > 0:
        present_room_types.add("parking")

    normalized: list[VastuRuleReasoning] = []

    for rule_id in sorted(rules_by_id):
        catalog_rule = rules_by_id[rule_id]
        item = raw_by_id.get(rule_id)

        if item is None:
            if catalog_rule.subject_room_types:
                applies = any(
                    normalize_room_type(room_type) in present_room_types
                    for room_type in catalog_rule.subject_room_types
                )

                applicability = (
                    RuleApplicability.APPLICABLE if applies else RuleApplicability.NOT_APPLICABLE
                )
            else:
                applicability = RuleApplicability.CONTEXT_DEPENDENT

            item = VastuRuleReasoning(
                rule_id=rule_id,
                applicability=applicability,
                importance=catalog_rule.default_importance,
                flexibility=catalog_rule.default_flexibility,
                weight_multiplier_basis_points=10_000,
                rationale=(
                    "The reasoning provider omitted this catalog rule. "
                    "The application deterministically restored the catalog "
                    "default and inferred applicability from the confirmed "
                    "program."
                ),
            )

        importance = item.importance
        flexibility = item.flexibility
        multiplier = item.weight_multiplier_basis_points

        if not catalog_rule.reasoning_adjustable:
            importance = catalog_rule.default_importance
            flexibility = catalog_rule.default_flexibility
            multiplier = 10_000
        else:
            if importance not in catalog_rule.allowed_importance:
                raise VastuReasoningProviderError(
                    f"{rule_id}: importance {importance.value} is outside catalog policy."
                )
            if flexibility not in catalog_rule.allowed_flexibility:
                raise VastuReasoningProviderError(
                    f"{rule_id}: flexibility {flexibility.value} is outside catalog policy."
                )

        normalized.append(
            VastuRuleReasoning(
                rule_id=rule_id,
                applicability=item.applicability,
                importance=importance,
                flexibility=flexibility,
                weight_multiplier_basis_points=multiplier,
                rationale=item.rationale,
            )
        )

    mode = influence_mode_for_confirmed(request.confirmed)
    architecture_weight, vastu_weight = _MODE_WEIGHTS[mode]

    return VastuReasoningProfile(
        project_id=request.confirmed.project_id,
        draft_id=request.confirmed.draft_id,
        provider=raw.provider,
        model=raw.model,
        influence_mode=mode,
        architecture_weight_basis_points=architecture_weight,
        vastu_weight_basis_points=vastu_weight,
        rules=tuple(normalized),
        notes=(
            *raw.notes,
            "Vastu remains a soft influence; hard_constraint=false for every "
            "Phase 26B catalog rule.",
        ),
    ).with_content_hash()


class VastuReasoningService:
    def __init__(self, provider: VastuReasoningProvider) -> None:
        self._provider = provider

    def reason(
        self,
        *,
        confirmed: ConfirmedRequirements,
        original_prompt: str,
    ) -> VastuReasoningProfile:
        catalog = load_soft_vastu_catalog()
        request = VastuReasoningInput(
            confirmed=confirmed,
            original_prompt=original_prompt,
            catalog=catalog,
        )
        try:
            raw = self._provider.reason(request)
            if raw.project_id != confirmed.project_id:
                raise VastuReasoningProviderError("Vastu project identity mismatch.")
            if raw.draft_id != confirmed.draft_id:
                raise VastuReasoningProviderError("Vastu draft identity mismatch.")
            return _normalize_profile(raw, request)
        except VastuReasoningProviderError:
            raise
        except Exception as exc:
            raise VastuReasoningProviderError(str(exc)) from exc


def create_vastu_reasoning_service() -> VastuReasoningService:
    return VastuReasoningService(create_vastu_reasoning_provider())
