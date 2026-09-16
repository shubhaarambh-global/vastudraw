"use client";

import type { PlanDocument } from "@ai-vastu/contracts";
import { useMemo, useState } from "react";

import {
  configuredApiBaseUrl,
  ProjectApiClient,
  type GenerationResultSummary,
} from "../../api/client.ts";
import { browserAccessToken } from "../../auth/browser.ts";

interface ProjectWorkflowPanelProps {
  readonly document: PlanDocument;
  readonly onDocumentLoaded: (document: PlanDocument) => void;
}

function nextRevisionDocument(
  document: PlanDocument,
  projectId: string,
): PlanDocument {
  return {
    ...document,
    project_id: projectId,
    revision_id: crypto.randomUUID(),
    content_hash: null,
  };
}

export function ProjectWorkflowPanel(props: ProjectWorkflowPanelProps) {
  const api = useMemo(
    () =>
      new ProjectApiClient(configuredApiBaseUrl(), fetch, browserAccessToken),
    [],
  );
  const [projectId, setProjectId] = useState(props.document.project_id);
  const [projectName, setProjectName] = useState("AI Vastu project");
  const [currentRevisionId, setCurrentRevisionId] = useState<string | null>(
    null,
  );
  const [generationJson, setGenerationJson] = useState("");
  const [generationResult, setGenerationResult] =
    useState<GenerationResultSummary | null>(null);
  const [status, setStatus] = useState("API workflow idle");
  const [busy, setBusy] = useState(false);

  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    try {
      await operation();
    } catch (error) {
      setStatus(
        error instanceof Error ? error.message : "Unknown API workflow error",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="workflow-panel" aria-label="Project API workflow">
      <div className="workflow-heading">
        <div>
          <p className="eyebrow">Phase 19 · authenticated web/API workflow</p>
          <h2>Project revisions and generation</h2>
        </div>
        <span className="status-pill">{status}</span>
      </div>

      <div className="workflow-grid">
        <label>
          Project ID
          <input
            value={projectId}
            onChange={(event) => {
              setProjectId(event.target.value);
            }}
          />
        </label>
        <label>
          Project name
          <input
            value={projectName}
            onChange={(event) => {
              setProjectName(event.target.value);
            }}
          />
        </label>
      </div>

      <div className="workflow-actions">
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            void run(async () => {
              const project = await api.createProject(projectName, projectId);
              setCurrentRevisionId(project.current_revision_id);
              setStatus(`Created project ${project.project_id}`);
            });
          }}
        >
          Create project
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            void run(async () => {
              const revision = await api.loadCurrentRevision(projectId);
              if (revision === null) {
                setCurrentRevisionId(null);
                setStatus("Project has no saved revision yet");
                return;
              }
              props.onDocumentLoaded(revision.document);
              setCurrentRevisionId(revision.revision_id);
              setStatus(`Loaded revision ${String(revision.revision_number)}`);
            });
          }}
        >
          Load current
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            void run(async () => {
              const document = nextRevisionDocument(props.document, projectId);
              const revision = await api.appendRevision(projectId, {
                document,
                expected_parent_revision_id: currentRevisionId,
                note: "Saved from Phase 17 web/API workflow",
              });
              props.onDocumentLoaded(revision.document);
              setCurrentRevisionId(revision.revision_id);
              setStatus(`Saved revision ${String(revision.revision_number)}`);
            });
          }}
        >
          Save canonical revision
        </button>
      </div>

      <label className="workflow-json">
        Explicit ArchitecturalGenerationRequest JSON
        <textarea
          rows={7}
          value={generationJson}
          placeholder="Paste the complete explicit generation request. Phase 17 does not invent missing geometry or solver inputs."
          onChange={(event) => {
            setGenerationJson(event.target.value);
          }}
        />
      </label>
      <div className="workflow-actions">
        <button
          type="button"
          disabled={busy || generationJson.trim().length === 0}
          onClick={() => {
            void run(async () => {
              const request: unknown = JSON.parse(generationJson);
              const result = await api.generateArchitectural(request);
              setGenerationResult(result);
              setStatus(`Generation ${result.disposition}`);
            });
          }}
        >
          Run deterministic generation
        </button>
      </div>
      {generationResult === null ? null : (
        <pre className="workflow-result">
          {JSON.stringify(generationResult, null, 2)}
        </pre>
      )}
    </section>
  );
}
