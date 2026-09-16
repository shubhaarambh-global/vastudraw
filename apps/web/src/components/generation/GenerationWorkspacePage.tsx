"use client";

import { useEffect, useMemo, useState } from "react";

import {
  configuredApiBaseUrl,
  ProjectApiClient,
  type GenerationIntakeRecord,
} from "../../api/client.ts";
import { browserAccessToken } from "../../auth/browser.ts";
import { useWorkspaceProjects } from "../dashboard/useWorkspaceProjects.ts";
import { SaasShell } from "../shell/SaasShell.tsx";

const MAX_FILES = 8;
const MAX_FILE_BYTES = 20 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "application/pdf"]);

interface UploadPreview {
  readonly file: File;
  readonly objectUrl: string | null;
}

function formatBytes(value: number): string {
  if (value >= 1024 * 1024) {
    return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  }
  return `${String(Math.max(1, Math.round(value / 1024)))} KB`;
}

function validateFiles(files: readonly File[]): string | null {
  if (files.length > MAX_FILES) {
    return `Upload at most ${String(MAX_FILES)} reference files.`;
  }
  for (const file of files) {
    if (!ACCEPTED_TYPES.has(file.type)) {
      return `${file.name}: only JPG, PNG, and PDF are supported.`;
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

export function GenerationWorkspacePage() {
  const workspace = useWorkspaceProjects();
  const [projectId, setProjectId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [previews, setPreviews] = useState<readonly UploadPreview[]>([]);
  const [status, setStatus] = useState(
    "Add a client brief and optional reference files.",
  );
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState<GenerationIntakeRecord | null>(null);
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

  return (
    <SaasShell userLabel={workspace.userLabel}>
      <div className="saas-page-heading">
        <div>
          <p className="saas-kicker">Multimodal client intake</p>
          <h1>Generation</h1>
          <p className="saas-muted">
            Capture the client prompt plus JPG, PNG, and PDF references without
            turning uploaded pixels or documents into authoritative geometry.
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
              <h2>Describe what should be generated</h2>
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
            <span>Generation prompt</span>
            <textarea
              maxLength={12_000}
              value={prompt}
              onChange={(event) => {
                setPrompt(event.target.value);
                setSaved(null);
              }}
              placeholder="Example: Plan a 3BHK residence for a 30 ft × 50 ft plot. Keep the kitchen in the South-East, master bedroom toward South/South-West, include one puja space, parking for one car, good daylight, and a practical stair location."
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
              <strong>Reference images and PDFs</strong>
              <p>
                Client sketches, inspiration, survey PDFs, existing plans, or
                reference images.
              </p>
            </div>
            <label className="generation-upload-button">
              Add files
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
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
                    <div className="generation-pdf-tile">PDF</div>
                  )}
                  <div>
                    <strong>{preview.file.name}</strong>
                    <small>
                      {preview.file.type === "application/pdf"
                        ? "PDF"
                        : "Image"}{" "}
                      · {formatBytes(preview.file.size)}
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
                Reference files guide the workflow only. Explicit dimensions and
                confirmed geometry remain required before canonical generation.
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
        </section>

        <aside className="generation-side-stack">
          <section className="saas-card">
            <p className="saas-kicker">Accepted inputs</p>
            <h2>Prompt + references</h2>
            <ul className="saas-check-list saas-check-list-large">
              <li>
                <strong>Text brief</strong>
                <span>Client intent and room requirements</span>
              </li>
              <li>
                <strong>JPG / PNG</strong>
                <span>Sketches, photos, precedent, hand drawings</span>
              </li>
              <li>
                <strong>PDF</strong>
                <span>Survey sheets, reference plans, client documents</span>
              </li>
            </ul>
          </section>

          <section className="saas-card">
            <p className="saas-kicker">Authority boundary</p>
            <h2>References are not geometry</h2>
            <p className="saas-muted">
              Phase 22 stores and hashes the client intake. It does not silently
              extract dimensions, walls, rooms, or plot geometry from an image
              or PDF.
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
