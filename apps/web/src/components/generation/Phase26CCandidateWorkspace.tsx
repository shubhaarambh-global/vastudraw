"use client";

import { useMemo, useState } from "react";

import {
  type AlternativePreviewResponse,
  type CandidateResult26C,
  ProjectApiClient,
  type SelectAlternativeResponse,
} from "../../api/client.ts";
import { ProfessionalPlanCanvas } from "./ProfessionalPlanCanvas.tsx";

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

  const candidate = useMemo(
    () =>
      preview.candidate_run.candidates.find(
        (item) => item.candidate_id === activeId,
      ) ??
      preview.candidate_run.candidates[0] ??
      null,
    [activeId, preview.candidate_run.candidates],
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
      setSelection(result);
    } catch (cause: unknown) {
      setError(
        cause instanceof Error ? cause.message : "Candidate selection failed.",
      );
    } finally {
      setSelecting(false);
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
              </div>
            ) : null}
          </div>
        </aside>
      </div>

      <footer className="phase26c3-workspace-footer">
        <button type="button" onClick={onStartOver}>
          Start another project
        </button>
        <div className="phase26c3-revision-preview">
          <span>Revision chat</span>
          <input
            disabled
            value=""
            placeholder="Phase 26D: e.g. make dining 1 ft wider…"
            readOnly
          />
          <button type="button" disabled>
            Send
          </button>
        </div>
      </footer>
    </section>
  );
}
