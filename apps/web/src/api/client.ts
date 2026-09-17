import type { PlanDocument } from "@ai-vastu/contracts";

export interface ProjectRecord {
  readonly project_id: string;
  readonly name: string;
  readonly created_at: string;
  readonly current_revision_id: string | null;
  readonly current_revision_number: number;
}

export interface RevisionRecord {
  readonly project_id: string;
  readonly revision_id: string;
  readonly revision_number: number;
  readonly parent_revision_id: string | null;
  readonly created_at: string;
  readonly document: PlanDocument;
  readonly plan_document_hash: string;
  readonly payload_hash: string;
}

export interface GenerationAttachmentRecord {
  readonly attachment_id: string;
  readonly kind: "IMAGE" | "PDF" | "DXF" | "DWG";
  readonly original_filename: string;
  readonly media_type: string;
  readonly size_bytes: number;
  readonly sha256: string;
  readonly storage_name: string;
}

export interface GenerationIntakeRecord {
  readonly intake_id: string;
  readonly project_id: string;
  readonly created_at: string;
  readonly prompt: string;
  readonly attachments: readonly GenerationAttachmentRecord[];
  readonly authoritative_geometry: false;
  readonly content_hash: string;
}

export interface PlanRoomObservation {
  readonly room_type: string;
  readonly label: string | null;
  readonly centroid_x_basis_points: number | null;
  readonly centroid_y_basis_points: number | null;
  readonly approximate_area_mm2: number | null;
  readonly confidence: number;
  readonly source: string;
  readonly requires_confirmation: boolean;
  readonly evidence: readonly string[];
}

export interface PlanRecognitionDraft {
  readonly schema_version: "26B.5.1";
  readonly project_id: string;
  readonly intake_id: string;
  readonly provider: string;
  readonly model: string | null;
  readonly reference_names: readonly string[];
  readonly envelope: {
    readonly geometry_type: "RECTANGLE" | "POLYGON" | "UNKNOWN";
    readonly width_mm: number | null;
    readonly depth_mm: number | null;
    readonly built_up_area_mm2: number | null;
    readonly confidence: number;
    readonly source: string;
    readonly requires_confirmation: boolean;
    readonly evidence: readonly string[];
  };
  readonly orientation: {
    readonly north_rotation_deg: number | null;
    readonly road_side: string | null;
    readonly entrance_facing: string | null;
    readonly confidence: number;
    readonly source: string;
    readonly requires_confirmation: boolean;
    readonly evidence: readonly string[];
  };
  readonly rooms: readonly PlanRoomObservation[];
  readonly observations: readonly string[];
  readonly questions: readonly string[];
  readonly warnings: readonly string[];
  readonly content_hash: string | null;
}

export interface PlanVastuAudit {
  readonly schema_version: "26B.5.1";
  readonly project_id: string;
  readonly intake_id: string;
  readonly status:
    | "SCORED"
    | "NEEDS_ORIENTATION"
    | "NEEDS_ROOM_POSITIONS"
    | "NO_EVALUABLE_RULES";
  readonly overall_basis_points: number | null;
  readonly evaluation_coverage_basis_points: number | null;
  readonly evaluated_weight: number;
  readonly unevaluated_weight: number;
  readonly provisional: true;
  readonly rules: readonly {
    readonly rule_id: string;
    readonly title: string;
    readonly status:
      | "PREFERRED"
      | "SECONDARY"
      | "NEUTRAL"
      | "AVOIDED"
      | "NOT_APPLICABLE"
      | "NOT_EVALUATED";
    readonly score_basis_points: number | null;
    readonly effective_weight: number;
    readonly evidence: readonly string[];
    readonly suggestion: string;
  }[];
  readonly suggestions: readonly string[];
  readonly notes: readonly string[];
  readonly content_hash: string | null;
}

export interface PlanAnalysisResult {
  readonly schema_version: "26B.5.1";
  readonly project_id: string;
  readonly intake_id: string;
  readonly recognition: PlanRecognitionDraft;
  readonly vastu_audit: PlanVastuAudit;
  readonly alternate_plan_envelope: {
    readonly geometry_type: "RECTANGLE" | "POLYGON" | "UNKNOWN";
    readonly width_mm: number | null;
    readonly depth_mm: number | null;
    readonly exact_area_mm2: number | null;
    readonly ready_for_exact_alternatives: boolean;
    readonly requires_user_confirmation: boolean;
    readonly reason: string;
  };
  readonly content_hash: string | null;
}

export interface PlanGeometryConfirmationInput {
  readonly width_mm: number;
  readonly depth_mm: number;
  readonly north_rotation_deg: number;
  readonly road_side?: string | null;
  readonly entrance_facing?: string | null;
  readonly preserve_outer_envelope: true;
}

export interface PlanGeometryConfirmationRecord {
  readonly schema_version: "26B.5.1";
  readonly project_id: string;
  readonly intake_id: string;
  readonly width_mm: number;
  readonly depth_mm: number;
  readonly exact_area_mm2: number;
  readonly north_rotation_deg: number;
  readonly road_side: string | null;
  readonly entrance_facing: string | null;
  readonly preserve_outer_envelope: true;
  readonly confirmed_by_user: true;
  readonly content_hash: string | null;
}

export interface GenerationResultSummary {
  readonly disposition: "ACCEPTED" | "REJECTED" | "UNSOLVED";
  readonly content_hash: string | null;
  readonly [key: string]: unknown;
}

export interface AppendRevisionInput {
  readonly document: PlanDocument;
  readonly expected_parent_revision_id: string | null;
  readonly note?: string;
}

export type AccessTokenProvider = () => Promise<string | null>;

export class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

function trimTrailingSlash(value: string): string {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

async function responseDetail(response: Response): Promise<string> {
  const text = await response.text();
  if (text.trim().length === 0) {
    return response.statusText || `HTTP ${String(response.status)}`;
  }
  try {
    const payload: unknown = JSON.parse(text);
    if (
      typeof payload === "object" &&
      payload !== null &&
      "detail" in payload &&
      typeof payload.detail === "string"
    ) {
      return payload.detail;
    }
  } catch {
    // Preserve the response body as the most useful failure detail.
  }
  return text;
}

export class ProjectApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly accessTokenProvider: AccessTokenProvider | null;

  constructor(
    baseUrl: string,
    fetchImpl: typeof fetch = fetch,
    accessTokenProvider: AccessTokenProvider | null = null,
  ) {
    this.fetchImpl = fetchImpl.bind(globalThis);
    this.accessTokenProvider = accessTokenProvider;

    const normalized = baseUrl.trim();
    if (normalized.length === 0) {
      throw new TypeError("API base URL must not be empty.");
    }
    this.baseUrl = trimTrailingSlash(normalized);
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const headers = new Headers(init?.headers);
    const token = await this.accessTokenProvider?.();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      ...init,
      headers,
    });
    if (!response.ok) {
      throw new ApiRequestError(
        await responseDetail(response),
        response.status,
      );
    }
    return (await response.json()) as T;
  }

  async listProjects(): Promise<readonly ProjectRecord[]> {
    return this.request<readonly ProjectRecord[]>("/projects");
  }

  async createProject(name: string, projectId: string): Promise<ProjectRecord> {
    return this.request<ProjectRecord>("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, project_id: projectId }),
    });
  }

  async getProject(projectId: string): Promise<ProjectRecord> {
    return this.request<ProjectRecord>(
      `/projects/${encodeURIComponent(projectId)}`,
    );
  }

  async getRevision(
    projectId: string,
    revisionId: string,
  ): Promise<RevisionRecord> {
    return this.request<RevisionRecord>(
      `/projects/${encodeURIComponent(projectId)}/revisions/${encodeURIComponent(revisionId)}`,
    );
  }

  async loadCurrentRevision(projectId: string): Promise<RevisionRecord | null> {
    const project = await this.getProject(projectId);
    if (project.current_revision_id === null) {
      return null;
    }
    return this.getRevision(projectId, project.current_revision_id);
  }

  async appendRevision(
    projectId: string,
    input: AppendRevisionInput,
  ): Promise<RevisionRecord> {
    return this.request<RevisionRecord>(
      `/projects/${encodeURIComponent(projectId)}/revisions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    );
  }

  async createGenerationIntake(
    projectId: string,
    prompt: string,
    files: readonly File[],
  ): Promise<GenerationIntakeRecord> {
    const form = new FormData();
    form.set("prompt", prompt);
    for (const file of files) {
      form.append("files", file, file.name);
    }
    return this.request<GenerationIntakeRecord>(
      `/projects/${encodeURIComponent(projectId)}/generation-intakes`,
      { method: "POST", body: form },
    );
  }

  async listGenerationIntakes(
    projectId: string,
  ): Promise<readonly GenerationIntakeRecord[]> {
    return this.request<readonly GenerationIntakeRecord[]>(
      `/projects/${encodeURIComponent(projectId)}/generation-intakes`,
    );
  }

  async analyzeGenerationIntakePlan(
    projectId: string,
    intakeId: string,
  ): Promise<PlanAnalysisResult> {
    return this.request<PlanAnalysisResult>(
      `/projects/${encodeURIComponent(projectId)}/generation-intakes/${encodeURIComponent(intakeId)}/plan-analysis`,
      { method: "POST" },
    );
  }

  async getGenerationIntakePlanAnalysis(
    projectId: string,
    intakeId: string,
  ): Promise<PlanAnalysisResult> {
    return this.request<PlanAnalysisResult>(
      `/projects/${encodeURIComponent(projectId)}/generation-intakes/${encodeURIComponent(intakeId)}/plan-analysis`,
    );
  }

  async confirmGenerationIntakePlanGeometry(
    projectId: string,
    intakeId: string,
    input: PlanGeometryConfirmationInput,
  ): Promise<PlanGeometryConfirmationRecord> {
    return this.request<PlanGeometryConfirmationRecord>(
      `/projects/${encodeURIComponent(projectId)}/generation-intakes/${encodeURIComponent(intakeId)}/plan-confirmation`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(input),
      },
    );
  }

  async generateArchitectural(
    request: unknown,
  ): Promise<GenerationResultSummary> {
    return this.request<GenerationResultSummary>("/generation/architectural", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  }
}

export function configuredApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_AI_VASTU_API_BASE_URL?.trim();
  return configured && configured.length > 0
    ? configured
    : "http://127.0.0.1:8000";
}
