from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_confirmed_generation_routes() -> None:
    path = ROOT / "apps/api/app/confirmed_generation_routes.py"
    text = path.read_text(encoding="utf-8")

    candidate_import = """from ai_vastu.requirements.candidate_orchestrator import (
    CandidateGenerationOrchestrator,
    CandidateSelectionError,
    GenerateAlternativesOptions,
    SelectAlternativeOptions,
)
"""
    if candidate_import not in text:
        marker = "from ai_vastu.requirements.final_orchestrator import (\n"
        if marker not in text:
            raise SystemExit("Could not locate confirmed-generation import marker.")
        text = text.replace(marker, candidate_import + marker, 1)

    multi_import = "from ai_vastu.multi_candidate import MultiCandidateGenerationError\n"
    if multi_import not in text:
        marker = (
            "from ai_vastu.projects.factory import create_project_repository_from_environment\n"
        )
        if marker not in text:
            raise SystemExit("Could not locate project factory import marker.")
        text = text.replace(marker, multi_import + marker, 1)

    project_error_import = (
        "from ai_vastu.projects.errors import ProjectNotFoundError, RevisionConflictError\n"
    )
    if project_error_import not in text:
        marker = (
            "from ai_vastu.projects.factory import create_project_repository_from_environment\n"
        )
        if marker not in text:
            raise SystemExit("Could not locate project factory import marker.")
        text = text.replace(marker, project_error_import + marker, 1)

    endpoints = """
@router.post("/projects/{project_id}/alternatives")
def generate_confirmed_alternatives(
    project_id: UUID,
    options: GenerateAlternativesOptions,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    billing_repository = create_billing_repository()
    project_repository = create_project_repository_from_environment()
    try:
        orchestrator = CandidateGenerationOrchestrator(
            requirements_store=RequirementsStore.from_environment(),
            billing_service=BillingService(billing_repository),
            project_service=ProjectRevisionService(project_repository),
        )
        preview = orchestrator.preview(
            authenticated_user_id=user_id,
            project_id=project_id,
            draft_id=options.draft_id,
            max_alternatives=options.max_alternatives,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Confirmed requirements were not found.",
        ) from exc
    except EntitlementDenied as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ArchitecturalIntelligenceConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ArchitecturalIntelligenceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except VastuReasoningConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VastuReasoningProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (
        MultiCandidateGenerationError,
        UnsupportedConfirmedRequirement,
        Phase24FinalizationError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        billing_repository.close()
        project_repository.close()

    return {
        "candidate_run": preview.outcome.run.model_dump(mode="json"),
        "billing_reason": preview.billing_reason,
        "quota_consumed": False,
        "revision_persisted": False,
        "architectural_intent": (
            None
            if preview.architectural_intent is None
            else preview.architectural_intent.model_dump(mode="json")
        ),
        "vastu_reasoning_profile": (
            None
            if preview.vastu_reasoning_profile is None
            else preview.vastu_reasoning_profile.model_dump(mode="json")
        ),
    }


@router.post("/projects/{project_id}/alternatives/select")
def select_confirmed_alternative(
    project_id: UUID,
    options: SelectAlternativeOptions,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = _resolve_user_id(authorization)
    billing_repository = create_billing_repository()
    project_repository = create_project_repository_from_environment()
    try:
        orchestrator = CandidateGenerationOrchestrator(
            requirements_store=RequirementsStore.from_environment(),
            billing_service=BillingService(billing_repository),
            project_service=ProjectRevisionService(project_repository),
        )
        selection = orchestrator.select(
            authenticated_user_id=user_id,
            project_id=project_id,
            options=options,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Confirmed requirements were not found.",
        ) from exc
    except EntitlementDenied as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RevisionConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except CandidateSelectionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        billing_repository.close()
        project_repository.close()

    revision = selection.revision
    return {
        "revision_persisted": True,
        "successful_generation_recorded": selection.successful_generation_recorded,
        "billing_reason": selection.billing_reason,
        "revision_id": str(revision.revision_id),
        "revision_number": revision.revision_number,
        "plan_document_hash": revision.plan_document_hash,
        "editor_path": f"/editor?project={project_id}",
    }


"""

    marker = '@router.post("/projects/{project_id}")\n'
    if '"/projects/{project_id}/alternatives"' not in text:
        if marker not in text:
            raise SystemExit("Could not locate existing confirmed-generation endpoint.")
        text = text.replace(marker, endpoints + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_client() -> None:
    path = ROOT / "apps/web/src/api/client.ts"
    text = path.read_text(encoding="utf-8")

    interfaces = """export interface RequirementDraft26C {
  readonly schema_version: "24A.1";
  readonly draft_id: string;
  readonly user_id: string;
  readonly project_id: string;
  readonly prompt: string;
  readonly provider: string;
  readonly model: string | null;
}

export interface RequirementInterpretResponse {
  readonly draft: RequirementDraft26C;
  readonly ready_for_confirmation: boolean;
}

export interface ConfirmedRoomRequirementInput {
  readonly room_type: string;
  readonly quantity: number;
  readonly floor_preference: number | null;
  readonly notes: string | null;
}

export interface ConfirmedRequirementsInput {
  readonly schema_version: "24A.1";
  readonly draft_id: string;
  readonly user_id: string;
  readonly project_id: string;
  readonly user_confirmed: true;
  readonly plot_width_mm: number;
  readonly plot_depth_mm: number;
  readonly north_rotation_deg: number;
  readonly road_side: "N" | "E" | "S" | "W";
  readonly entrance_facing: "N" | "E" | "S" | "W" | null;
  readonly floor_count: 1;
  readonly bedroom_count: number;
  readonly parking_count: number;
  readonly vastu_mode: "space_efficient" | "balanced" | "strict";
  readonly rooms: ConfirmedRoomRequirementInput[];
}

export interface ConfirmedRequirementsResponse {
  readonly confirmed: ConfirmedRequirementsInput;
}

export interface CandidateStrategy26C {
  readonly strategy_id: string;
  readonly kind: string;
  readonly label: string;
  readonly description: string;
  readonly deterministic_ordinal: number;
}

export interface CandidateExplanation26C {
  readonly strengths: readonly string[];
  readonly compromises: readonly string[];
  readonly selection_reason: string;
}

export interface CandidateResult26C {
  readonly candidate_id: string;
  readonly rank: number;
  readonly strategy: CandidateStrategy26C;
  readonly valid_architecture: true;
  readonly architecture_score_basis_points: number;
  readonly vastu_score_basis_points: number | null;
  readonly vastu_evaluation_coverage_basis_points: number | null;
  readonly combined_score_basis_points: number;
  readonly architecture_weight_basis_points: number;
  readonly vastu_weight_basis_points: number;
  readonly plan_document_hash: string | null;
  readonly plan_document: PlanDocument | null;
  readonly soft_vastu_suggestions: readonly string[];
  readonly unevaluated_metrics: readonly string[];
  readonly explanation: CandidateExplanation26C;
}

export interface AlternativePreviewResponse {
  readonly candidate_run: {
    readonly schema_version: "26C.2";
    readonly project_id: string;
    readonly planning_mode: "practical" | "balanced" | "vastu_forward";
    readonly candidates: readonly CandidateResult26C[];
    readonly attempted_candidate_count: number;
    readonly rejected_candidate_count: number;
    readonly structural_design_included: false;
    readonly content_hash: string;
  };
  readonly billing_reason: string;
  readonly quota_consumed: false;
  readonly revision_persisted: false;
  readonly architectural_intent: unknown;
  readonly vastu_reasoning_profile: unknown;
}

export interface GenerateAlternativesInput {
  readonly draft_id: string;
  readonly accept_profile_defaults: true;
  readonly max_alternatives: number;
}

export interface SelectAlternativeInput {
  readonly draft_id: string;
  readonly candidate_run_hash: string;
  readonly candidate_id: string;
  readonly plan_document: PlanDocument;
}

export interface SelectAlternativeResponse {
  readonly revision_persisted: true;
  readonly successful_generation_recorded: boolean;
  readonly billing_reason: string;
  readonly revision_id: string;
  readonly revision_number: number;
  readonly plan_document_hash: string;
  readonly editor_path: string;
}

"""

    marker = "export interface GenerationResultSummary {\n"
    if "export interface AlternativePreviewResponse" not in text:
        if marker not in text:
            raise SystemExit("Could not locate client interface insertion marker.")
        text = text.replace(marker, interfaces + marker, 1)

    methods = """  async interpretRequirements(
    projectId: string,
    prompt: string,
  ): Promise<RequirementInterpretResponse> {
    const form = new FormData();
    form.set("project_id", projectId);
    form.set("prompt", prompt);
    return this.request<RequirementInterpretResponse>("/requirements/interpret", {
      method: "POST",
      body: form,
    });
  }

  async confirmRequirements(
    draftId: string,
    input: ConfirmedRequirementsInput,
  ): Promise<ConfirmedRequirementsResponse> {
    return this.request<ConfirmedRequirementsResponse>(
      `/requirements/drafts/${encodeURIComponent(draftId)}/confirm`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    );
  }

  async generateConfirmedAlternatives(
    projectId: string,
    input: GenerateAlternativesInput,
  ): Promise<AlternativePreviewResponse> {
    return this.request<AlternativePreviewResponse>(
      `/confirmed-generation/projects/${encodeURIComponent(projectId)}/alternatives`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    );
  }

  async selectConfirmedAlternative(
    projectId: string,
    input: SelectAlternativeInput,
  ): Promise<SelectAlternativeResponse> {
    return this.request<SelectAlternativeResponse>(
      `/confirmed-generation/projects/${encodeURIComponent(projectId)}/alternatives/select`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    );
  }

"""

    marker = "  async generateArchitectural(\n"
    if "async generateConfirmedAlternatives(" not in text:
        if marker not in text:
            raise SystemExit("Could not locate client method insertion marker.")
        text = text.replace(marker, methods + marker, 1)

    path.write_text(text, encoding="utf-8")


def patch_css_import() -> None:
    path = ROOT / "apps/web/src/app/globals.css"
    text = path.read_text(encoding="utf-8")
    line = '@import "../components/generation/phase26c3.css";\n'
    if line in text:
        return

    existing = '@import "../components/generation/phase26c.css";\n'
    text = text.replace(existing, existing + line, 1) if existing in text else line + text

    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_confirmed_generation_routes()
    patch_client()
    patch_css_import()
    print("Phase 26C.3 overlay applied.")


if __name__ == "__main__":
    main()
