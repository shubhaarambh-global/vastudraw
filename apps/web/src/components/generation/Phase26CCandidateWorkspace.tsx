"use client";

import { useMemo, useState } from "react";

import {
  type AlternativePreviewResponse,
  type CandidateResult26C,
  type ProductionExportFormat,
  ProjectApiClient,
  type SelectAlternativeResponse,
} from "../../api/client.ts";
import { ProfessionalPlanCanvas } from "./ProfessionalPlanCanvas.tsx";
import { RevisionChatPanel } from "../editor/RevisionChatPanel.tsx";

interface CandidateWorkspaceProps {
  readonly api: ProjectApiClient;
  readonly projectId: string;
  readonly draftId: string;
  readonly preview: AlternativePreviewResponse;
  readonly onStartOver: () => void;
}

function scoreText(value: number | null): string {
  return value === null ? "Not evaluated" : (value / 100).toFixed(1);
}

const exportFormats: readonly ProductionExportFormat[] = [
  "PDF",
  "SVG",
  "JPEG",
  "DXF",
];

function CandidateMetrics({
  candidate,
}: {
  readonly candidate: CandidateResult26C;
}) {
  return (
    <div className="phase26c3-metrics">
      <div>
        <span>Measured objectives</span>
        <strong>{scoreText(candidate.architecture_score_basis_points)}</strong>
      </div>
      <div>
        <span>Vastu</span>
        <strong>{scoreText(candidate.vastu_score_basis_points)}</strong>
      </div>
      <div>
        <span>Coverage</span>
        <strong>
          {candidate.vastu_evaluation_coverage_basis_points === null
            ? "N/A"
            : `${scoreText(candidate.vastu_evaluation_coverage_basis_points)}%`}
        </strong>
      </div>
      <div>
        <span>Current blend</span>
        <strong>{scoreText(candidate.combined_score_basis_points)}</strong>
      </div>
    </div>
  );
}

export function Phase26CCandidateWorkspace({
  api,
  projectId,
  draftId,
  preview,
  onStartOver,
}: CandidateWorkspaceProps) {
  const [activeId, setActiveId] = useState(
    preview.candidate_run.candidates[0]?.candidate_id ?? "",
  );
  const [selecting, setSelecting] = useState(false);
  const [selection, setSelection] = useState<SelectAlternativeResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [exportFloorIndex, setExportFloorIndex] = useState(0);
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const candidate = useMemo(
    () =>
      preview.candidate_run.candidates.find(
        (item) => item.candidate_id === activeId,
      ) ??
      preview.candidate_run.candidates[0] ??
      null,
    [activeId, preview.candidate_run.candidates],
  );
  const candidateFloors = useMemo(
    () =>
      [...(candidate?.plan_document?.floors ?? [])].sort(
        (first, second) => first.index - second.index,
      ),
    [candidate],
  );

  if (candidate === null) {
    return (
      <section className="phase26c3-workspace">
        <h1>No ranked candidate survived validation.</h1>
      </section>
    );
  }

  async function selectCandidate() {
    const currentCandidate = candidate;

    if (currentCandidate === null) {
      setError("No candidate is currently selected.");
      return;
    }

    if (currentCandidate.plan_document === null) {
      setError("This candidate does not contain a canonical PlanDocument.");
      return;
    }

    setSelecting(true);
    setError(null);
    try {
      const result = await api.selectConfirmedAlternative(projectId, {
        draft_id: draftId,
        candidate_run_hash: preview.candidate_run.content_hash,
        candidate_id: currentCandidate.candidate_id,
        plan_document: currentCandidate.plan_document,
      });
      if (
        result.candidate_id !== currentCandidate.candidate_id ||
        result.plan_document_hash !== currentCandidate.plan_document_hash
      ) {
        throw new Error(
          "Saved revision identity did not match the selected candidate.",
        );
      }
      setSelection(result);
    } catch (cause: unknown) {
      setError(
        cause instanceof Error ? cause.message : "Candidate selection failed.",
      );
    } finally {
      setSelecting(false);
    }
  }

  async function downloadExport(
    format: ProductionExportFormat,
    scope: "FLOOR" | "ALL_FLOORS" = "FLOOR",
  ) {
    const currentSelection = selection;
    const currentCandidate = candidate;
    if (
      currentSelection === null ||
      currentCandidate === null ||
      currentCandidate.plan_document === null
    ) {
      setExportError("Select and save a canonical candidate before exporting.");
      return;
    }
    const requestKey = `${format}:${scope}:${String(exportFloorIndex)}`;
    setExporting(requestKey);
    setExportError(null);
    setExportStatus("Preparing the selected canonical plan...");
    try {
      const result = await api.downloadSelectedExport(projectId, {
        revision_id: currentSelection.revision_id,
        candidate_id: currentSelection.candidate_id,
        format,
        scope,
        floor_index: scope === "ALL_FLOORS" ? null : exportFloorIndex,
      });
      if (
        result.candidateId !== currentCandidate.candidate_id ||
        result.sourcePlanHash !== currentCandidate.plan_document_hash
      ) {
        throw new Error(
          "Downloaded artifact identity did not match the selected plan.",
        );
      }
      setExportStatus(`Downloading ${result.filename}...`);
      const objectUrl = URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = result.filename;
      link.hidden = true;
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(objectUrl);
      setExportStatus(`${result.filename} is ready.`);
    } catch (cause: unknown) {
      setExportStatus(null);
      setExportError(
        cause instanceof Error ? cause.message : "Export download failed.",
      );
    } finally {
      setExporting(null);
    }
  }

  return (
    <section className="phase26c3-workspace">
      <header className="phase26c3-workspace-head">
        <div>
          <p className="saas-kicker">Generated alternatives</p>
          <h1>Choose the plan to keep</h1>
          <p className="saas-muted">
            Every shown option passed hard architectural validation. Vastu is a
            soft traditional planning influence and its evaluation coverage is
            shown separately.
          </p>
        </div>
        <div className="phase26c3-run-meta">
          <span>{preview.candidate_run.planning_mode.replace("_", " ")}</span>
          <small>
            {String(preview.candidate_run.attempted_candidate_count)} strategies
            explored
          </small>
        </div>
      </header>

      <div
        className="phase26c3-tabs"
        role="tablist"
        aria-label="Generated alternatives"
      >
        {preview.candidate_run.candidates.map((item, index) => (
          <button
            key={item.candidate_id}
            type="button"
            role="tab"
            aria-selected={item.candidate_id === candidate.candidate_id}
            data-active={item.candidate_id === candidate.candidate_id}
            onClick={() => {
              setActiveId(item.candidate_id);
              setSelection(null);
              setError(null);
              setExportFloorIndex(0);
              setExportStatus(null);
              setExportError(null);
            }}
          >
            <span>{String.fromCharCode(65 + index)}</span>
            <strong>Plan</strong>
            <small>{scoreText(item.combined_score_basis_points)}</small>
          </button>
        ))}
      </div>

      <div className="phase26c3-main-grid">
        <div className="phase26c3-canvas-card">
          <div className="phase26c3-canvas-head">
            <div>
              <span>Candidate {String(candidate.rank)}</span>
              <strong>{`Plan ${String.fromCharCode(64 + candidate.rank)}`}</strong>
            </div>
            <span className="saas-status-badge" data-tone="green">
              Hard-valid
            </span>
          </div>
          <ProfessionalPlanCanvas document={candidate.plan_document} />
        </div>

        <aside className="phase26c3-insights">
          <CandidateMetrics candidate={candidate} />

          <section>
            <p className="saas-kicker">Why this option</p>
            <h2>Measured strengths</h2>
            <ul>
              {candidate.explanation.strengths.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section>
            <p className="saas-kicker">Trade-offs</p>
            <h2>Compromises & limits</h2>
            {candidate.explanation.compromises.length === 0 ? (
              <p className="saas-muted">
                No additional measured compromise was recorded.
              </p>
            ) : (
              <ul>
                {candidate.explanation.compromises.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}
            {candidate.unevaluated_metrics.length > 0 ? (
              <p className="phase26c3-evidence-note">
                Not yet scoreable: {candidate.unevaluated_metrics.join(", ")}.
              </p>
            ) : null}
          </section>

          {candidate.soft_vastu_suggestions.length > 0 ? (
            <section>
              <p className="saas-kicker">Traditional Vastu guidance</p>
              <h2>Suggestions</h2>
              <ul>
                {candidate.soft_vastu_suggestions.slice(0, 5).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <div className="phase26c3-selection">
            <button
              type="button"
              className="saas-button-primary"
              disabled={selecting || selection !== null}
              onClick={() => {
                void selectCandidate();
              }}
            >
              {selecting
                ? "Saving selected plan…"
                : selection
                  ? "Plan selected"
                  : "Select this plan"}
            </button>

            {error ? <p className="phase26c3-error">{error}</p> : null}

            {selection ? (
              <div className="phase26c3-success">
                <strong>
                  Revision {String(selection.revision_number)} saved
                </strong>
                <span>
                  Quota was recorded only after the durable revision existed.
                </span>
                <a
                  className="saas-link-button saas-link-button-primary"
                  href={selection.editor_path}
                >
                  Open selected plan →
                </a>

                <section
                  className="phase26c3-export-panel"
                  aria-label="Download selected plan"
                >
                  <div className="phase26c3-export-heading">
                    <div>
                      <strong>Download selected plan</strong>
                      <span>
                        Exports use revision {String(selection.revision_number)}{" "}
                        without regenerating geometry.
                      </span>
                    </div>
                    {candidateFloors.length > 1 ? (
                      <select
                        aria-label="Floor to export"
                        value={exportFloorIndex}
                        disabled={exporting !== null}
                        onChange={(event) => {
                          setExportFloorIndex(Number(event.target.value));
                          setExportStatus(null);
                          setExportError(null);
                        }}
                      >
                        {candidateFloors.map((floor) => (
                          <option key={floor.id} value={floor.index}>
                            {floor.name}
                          </option>
                        ))}
                      </select>
                    ) : null}
                  </div>

                  <div className="phase26c3-export-actions">
                    {exportFormats.map((format) => (
                      <button
                        key={format}
                        type="button"
                        disabled={exporting !== null}
                        onClick={() => {
                          void downloadExport(format);
                        }}
                      >
                        {exporting?.startsWith(`${format}:FLOOR`)
                          ? `Preparing ${format}...`
                          : format}
                      </button>
                    ))}
                  </div>

                  {candidateFloors.length > 1 ? (
                    <button
                      className="phase26c3-export-combined"
                      type="button"
                      disabled={exporting !== null}
                      onClick={() => {
                        void downloadExport("PDF", "ALL_FLOORS");
                      }}
                    >
                      {exporting?.includes("ALL_FLOORS")
                        ? "Preparing combined PDF..."
                        : `Combined PDF · ${String(candidateFloors.length)} floors`}
                    </button>
                  ) : null}

                  {exportStatus ? (
                    <p className="phase26c3-export-status" role="status">
                      {exportStatus}
                    </p>
                  ) : null}
                  {exportError ? (
                    <p className="phase26c3-error" role="alert">
                      {exportError}
                    </p>
                  ) : null}
                </section>
              </div>
            ) : null}
          </div>
        </aside>
      </div>

      <footer className="phase26c3-workspace-footer">
        <button type="button" onClick={onStartOver}>
          Start another project
        </button>
        {selection ? (
          <RevisionChatPanel
            api={api}
            projectId={projectId}
            baseRevisionId={selection.revision_id}
          />
        ) : (
          <p>Save a candidate to enable revision chat.</p>
        )}
      </footer>
    </section>
  );
}
