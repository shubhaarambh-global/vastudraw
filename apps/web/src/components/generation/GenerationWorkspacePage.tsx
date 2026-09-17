"use client";

import { useEffect, useMemo, useState } from "react";

import {
  configuredApiBaseUrl,
  ProjectApiClient,
  type GenerationIntakeRecord,
  type PlanAnalysisResult,
} from "../../api/client.ts";
import { browserAccessToken } from "../../auth/browser.ts";
import { useWorkspaceProjects } from "../dashboard/useWorkspaceProjects.ts";
import { SaasShell } from "../shell/SaasShell.tsx";

const MAX_FILES = 8;
const MAX_FILE_BYTES = 20 * 1024 * 1024;
const ACCEPTED_EXTENSIONS = new Set([
  ".jpg",
  ".jpeg",
  ".png",
  ".pdf",
  ".dxf",
  ".dwg",
]);

interface UploadPreview {
  readonly file: File;
  readonly objectUrl: string | null;
}

function extensionOf(filename: string): string {
  const index = filename.lastIndexOf(".");
  return index >= 0 ? filename.slice(index).toLowerCase() : "";
}

function formatBytes(value: number): string {
  if (value >= 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${String(Math.max(1, Math.round(value / 1024)))} KB`;
}

function referenceLabel(file: File): string {
  const extension = extensionOf(file.name);
  if (extension === ".pdf") return "PDF";
  if (extension === ".dxf") return "DXF";
  if (extension === ".dwg") return "DWG";
  return "Image";
}

function validateFiles(files: readonly File[]): string | null {
  if (files.length > MAX_FILES) {
    return `Upload at most ${String(MAX_FILES)} reference files.`;
  }
  for (const file of files) {
    if (!ACCEPTED_EXTENSIONS.has(extensionOf(file.name))) {
      return `${file.name}: only JPG, PNG, PDF, DXF, and DWG are supported.`;
    }
    if (file.size === 0) {
      return `${file.name}: empty files are not accepted.`;
    }
    if (file.size > MAX_FILE_BYTES) {
      return `${file.name}: each file must be 20 MB or smaller.`;
    }
  }
  return null;
}

function formatScore(basisPoints: number | null): string {
  if (basisPoints === null) return "Not available";
  return `${(basisPoints / 100).toFixed(1)} / 100`;
}

export function GenerationWorkspacePage() {
  const workspace = useWorkspaceProjects();
  const [projectId, setProjectId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [previews, setPreviews] = useState<readonly UploadPreview[]>([]);
  const [status, setStatus] = useState(
    "Add a client brief and optional reference files.",
  );
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [saved, setSaved] = useState<GenerationIntakeRecord | null>(null);
  const [analysis, setAnalysis] = useState<PlanAnalysisResult | null>(null);
  const [history, setHistory] = useState<readonly GenerationIntakeRecord[]>([]);

  const api = useMemo(
    () =>
      new ProjectApiClient(configuredApiBaseUrl(), fetch, browserAccessToken),
    [],
  );

  useEffect(() => {
    if (projectId.length === 0 && workspace.projects.length > 0) {
      setProjectId(workspace.projects[0]?.project_id ?? "");
    }
  }, [projectId, workspace.projects]);

  useEffect(() => {
    if (!projectId) {
      setHistory([]);
      return;
    }
    void api
      .listGenerationIntakes(projectId)
      .then(setHistory)
      .catch(() => {
        setHistory([]);
      });
  }, [api, projectId]);

  useEffect(() => {
    return () => {
      for (const preview of previews) {
        if (preview.objectUrl) {
          URL.revokeObjectURL(preview.objectUrl);
        }
      }
    };
  }, [previews]);

  function replaceFiles(nextFiles: readonly File[]) {
    const validation = validateFiles(nextFiles);
    if (validation) {
      setStatus(validation);
      return;
    }
    for (const preview of previews) {
      if (preview.objectUrl) {
        URL.revokeObjectURL(preview.objectUrl);
      }
    }
    setPreviews(
      nextFiles.map((file) => ({
        file,
        objectUrl: file.type.startsWith("image/")
          ? URL.createObjectURL(file)
          : null,
      })),
    );
    setStatus(
      nextFiles.length === 0
        ? "No reference files selected."
        : `${String(nextFiles.length)} reference file(s) ready.`,
    );
    setSaved(null);
    setAnalysis(null);
  }

  function removeFile(index: number) {
    const next = previews.filter((_item, itemIndex) => itemIndex !== index);
    replaceFiles(next.map((item) => item.file));
  }

  async function submitBrief() {
    const normalizedPrompt = prompt.trim();
    if (!projectId) {
      setStatus("Choose a project before saving the generation brief.");
      return;
    }
    if (!normalizedPrompt) {
      setStatus("Generation prompt is required.");
      return;
    }
    setBusy(true);
    setSaved(null);
    setAnalysis(null);
    try {
      const intake = await api.createGenerationIntake(
        projectId,
        normalizedPrompt,
        previews.map((item) => item.file),
      );
      setSaved(intake);
      setHistory((current) => [...current, intake]);
      setStatus(
        `Generation brief saved with ${String(intake.attachments.length)} reference file(s).`,
      );
    } catch (error: unknown) {
      setStatus(
        error instanceof Error
          ? error.message
          : "Could not save generation brief.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function analyzeUploadedPlan() {
    if (!saved || saved.attachments.length === 0) {
      setStatus("Save an intake with a plan file before analysis.");
      return;
    }
    setAnalyzing(true);
    setAnalysis(null);
    setStatus(
      "Recognizing plan evidence and calculating a provisional Vastu audit…",
    );
    try {
      const result = await api.analyzeGenerationIntakePlan(
        saved.project_id,
        saved.intake_id,
      );
      setAnalysis(result);
      setStatus(
        result.vastu_audit.overall_basis_points === null
          ? "Plan recognized. More confirmed evidence is required for a Vastu score."
          : "Plan recognized and provisional Vastu audit completed.",
      );
    } catch (error: unknown) {
      setStatus(
        error instanceof Error
          ? error.message
          : "Could not analyze the uploaded plan.",
      );
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <SaasShell userLabel={workspace.userLabel}>
      <div className="saas-page-heading">
        <div>
          <p className="saas-kicker">Multimodal client intake</p>
          <h1>Generation</h1>
          <p className="saas-muted">
            Start from a prompt, or upload an existing plan for recognition,
            provisional Vastu scoring, suggestions, and later exact-envelope
            alternatives.
          </p>
        </div>
        <span className="saas-status-badge" data-tone="green">
          Project-bound
        </span>
      </div>

      <div className="generation-layout">
        <section className="saas-card generation-compose-card">
          <div className="saas-card-heading">
            <div>
              <p className="saas-kicker">Client brief</p>
              <h2>Describe what should be generated or analyzed</h2>
            </div>
            <span className="generation-limit">12,000 characters</span>
          </div>

          <label className="saas-field generation-project-field">
            <span>Project</span>
            <select
              value={projectId}
              onChange={(event) => {
                setProjectId(event.target.value);
                setSaved(null);
                setAnalysis(null);
              }}
            >
              <option value="">Choose a project</option>
              {workspace.projects.map((project) => (
                <option key={project.project_id} value={project.project_id}>
                  {project.name}
                </option>
              ))}
            </select>
          </label>

          <label className="saas-field generation-prompt-field">
            <span>Generation / plan-analysis prompt</span>
            <textarea
              maxLength={12_000}
              value={prompt}
              onChange={(event) => {
                setPrompt(event.target.value);
                setSaved(null);
                setAnalysis(null);
              }}
              placeholder="Example: Audit this existing 30 ft × 50 ft plan for Vastu and suggest practical improvements without sacrificing circulation, privacy, or room usability."
            />
            <small>{String(prompt.length)} / 12,000</small>
          </label>

          <div
            className="generation-upload-zone"
            onDragOver={(event) => {
              event.preventDefault();
            }}
            onDrop={(event) => {
              event.preventDefault();
              const dropped = Array.from(event.dataTransfer.files);
              replaceFiles([...previews.map((item) => item.file), ...dropped]);
            }}
          >
            <div>
              <strong>Existing plans and references</strong>
              <p>
                Hand sketches, plan images, survey PDFs, vector PDFs, DXF, DWG,
                or visual references.
              </p>
            </div>
            <label className="generation-upload-button">
              Add files
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,.dxf,.dwg,image/jpeg,image/png,application/pdf"
                multiple
                onChange={(event) => {
                  const selected = Array.from(event.target.files ?? []);
                  replaceFiles([
                    ...previews.map((item) => item.file),
                    ...selected,
                  ]);
                  event.currentTarget.value = "";
                }}
              />
            </label>
            <small>
              Up to 8 files · 20 MB each · 50 MB combined server limit.
            </small>
          </div>

          {previews.length > 0 ? (
            <div className="generation-reference-grid">
              {previews.map((preview, index) => (
                <article key={`${preview.file.name}-${String(index)}`}>
                  {preview.objectUrl ? (
                    <img
                      src={preview.objectUrl}
                      alt="Client reference preview"
                    />
                  ) : (
                    <div className="generation-pdf-tile">
                      {referenceLabel(preview.file)}
                    </div>
                  )}
                  <div>
                    <strong>{preview.file.name}</strong>
                    <small>
                      {referenceLabel(preview.file)} ·{" "}
                      {formatBytes(preview.file.size)}
                    </small>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      removeFile(index);
                    }}
                  >
                    Remove
                  </button>
                </article>
              ))}
            </div>
          ) : null}

          <div className="generation-submit-row">
            <div>
              <strong>{status}</strong>
              <small>
                Recognition evidence is never silently promoted to authoritative
                CAD geometry. Exact-envelope alternatives require confirmation.
              </small>
            </div>
            <button
              className="saas-link-button saas-link-button-primary"
              type="button"
              disabled={busy || !workspace.authenticated}
              onClick={() => void submitBrief()}
            >
              {busy ? "Saving…" : "Save generation brief"}
            </button>
          </div>

          {saved && saved.attachments.length > 0 ? (
            <div className="generation-submit-row">
              <div>
                <strong>Existing-plan workflow</strong>
                <small>
                  Recognize rooms, plan orientation and dimensional evidence,
                  then calculate the soft Vastu audit.
                </small>
              </div>
              <button
                className="saas-link-button"
                type="button"
                disabled={analyzing || !workspace.authenticated}
                onClick={() => void analyzeUploadedPlan()}
              >
                {analyzing ? "Analyzing…" : "Analyze uploaded plan"}
              </button>
            </div>
          ) : null}

          {analysis ? (
            <section className="saas-card">
              <p className="saas-kicker">Uploaded-plan Vastu audit</p>
              <h2>{formatScore(analysis.vastu_audit.overall_basis_points)}</h2>
              <p className="saas-muted">
                Provisional score based on recognized evidence. Confirm geometry
                and North before exact alternate generation.
              </p>

              <ul className="saas-check-list saas-check-list-large">
                <li>
                  <strong>Rooms recognized</strong>
                  <span>{String(analysis.recognition.rooms.length)}</span>
                </li>
                <li>
                  <strong>Evaluation coverage</strong>
                  <span>
                    {analysis.vastu_audit.evaluation_coverage_basis_points ===
                    null
                      ? "Not available"
                      : `${(
                          analysis.vastu_audit
                            .evaluation_coverage_basis_points / 100
                        ).toFixed(1)}%`}
                  </span>
                </li>
                <li>
                  <strong>North rotation</strong>
                  <span>
                    {analysis.recognition.orientation.north_rotation_deg ===
                    null
                      ? "Needs confirmation"
                      : `${String(analysis.recognition.orientation.north_rotation_deg)}°`}
                  </span>
                </li>
                <li>
                  <strong>Envelope</strong>
                  <span>
                    {analysis.recognition.envelope.width_mm !== null &&
                    analysis.recognition.envelope.depth_mm !== null
                      ? `${String(analysis.recognition.envelope.width_mm)} × ${String(analysis.recognition.envelope.depth_mm)} mm`
                      : "Needs dimensional confirmation"}
                  </span>
                </li>
                <li>
                  <strong>Exact alternate plans</strong>
                  <span>
                    {analysis.alternate_plan_envelope
                      .ready_for_exact_alternatives
                      ? "Ready"
                      : "Confirmation required"}
                  </span>
                </li>
              </ul>

              {analysis.vastu_audit.suggestions.length > 0 ? (
                <>
                  <p className="saas-kicker">Suggestions</p>
                  <ul className="saas-check-list saas-check-list-large">
                    {analysis.vastu_audit.suggestions.map((suggestion) => (
                      <li key={suggestion}>
                        <span>{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}

              {analysis.recognition.questions.length > 0 ? (
                <>
                  <p className="saas-kicker">Needs confirmation</p>
                  <ul className="saas-check-list saas-check-list-large">
                    {analysis.recognition.questions.map((question) => (
                      <li key={question}>
                        <span>{question}</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
            </section>
          ) : null}
        </section>

        <aside className="generation-side-stack">
          <section className="saas-card">
            <p className="saas-kicker">Accepted inputs</p>
            <h2>Prompt + plan files</h2>
            <ul className="saas-check-list saas-check-list-large">
              <li>
                <strong>Text brief</strong>
                <span>Generate from requirements when no plan exists</span>
              </li>
              <li>
                <strong>JPG / PNG</strong>
                <span>Hand sketches and photographed/drawn plans</span>
              </li>
              <li>
                <strong>PDF</strong>
                <span>Scanned or vector architectural plan sheets</span>
              </li>
              <li>
                <strong>DXF</strong>
                <span>CAD extraction with units, text and vector evidence</span>
              </li>
              <li>
                <strong>DWG</strong>
                <span>Supported through a configured DWG-to-DXF backend</span>
              </li>
            </ul>
          </section>

          <section className="saas-card">
            <p className="saas-kicker">Authority boundary</p>
            <h2>Recognition is evidence</h2>
            <p className="saas-muted">
              AI may recognize the plan, but pixels and model inference never
              become authoritative millimetre geometry automatically. Critical
              envelope dimensions and North are confirmed before exact
              alternatives are generated.
            </p>
          </section>

          {history.length > 0 ? (
            <section className="saas-card generation-history-card">
              <p className="saas-kicker">Brief history</p>
              <h2>Saved client intakes</h2>
              <div className="generation-history-list">
                {[...history]
                  .reverse()
                  .slice(0, 5)
                  .map((item) => (
                    <article key={item.intake_id}>
                      <strong>{item.prompt}</strong>
                      <small>
                        {String(item.attachments.length)} reference file(s) ·{" "}
                        {new Date(item.created_at).toLocaleString()}
                      </small>
                    </article>
                  ))}
              </div>
            </section>
          ) : null}

          {saved ? (
            <section className="saas-card generation-saved-card">
              <p className="saas-kicker">Saved intake</p>
              <h2>Ready for structured interpretation</h2>
              <dl>
                <div>
                  <dt>Intake</dt>
                  <dd>{saved.intake_id}</dd>
                </div>
                <div>
                  <dt>References</dt>
                  <dd>{String(saved.attachments.length)}</dd>
                </div>
                <div>
                  <dt>Integrity</dt>
                  <dd>{saved.content_hash.slice(0, 12)}…</dd>
                </div>
              </dl>
            </section>
          ) : null}
        </aside>
      </div>
    </SaasShell>
  );
}
