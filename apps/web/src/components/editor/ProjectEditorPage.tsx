"use client";

import type { PlanDocument } from "@ai-vastu/contracts";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  configuredApiBaseUrl,
  ProjectApiClient,
  type ProjectRecord,
  type RevisionRecord,
} from "../../api/client.ts";
import { browserAccessToken } from "../../auth/browser.ts";
import { loadProjectWorkspace } from "../../editor/project-workspace.ts";
import type { EditorChangeSet } from "../../editor/types.ts";
import { PlanEditor } from "./PlanEditor.tsx";
import { ProjectContextPanel } from "./ProjectContextPanel.tsx";
import { RevisionChatPanel } from "./RevisionChatPanel.tsx";
import { RevisionHistoryPanel } from "./RevisionHistoryPanel.tsx";
import { RevisionExportPanel } from "./RevisionExportPanel.tsx";

interface ProjectEditorPageProps {
  readonly projectId: string | null;
}

interface LoadedWorkspace {
  readonly project: ProjectRecord;
  readonly revision: RevisionRecord | null;
}

type DimensionChange = Awaited<
  ReturnType<ProjectApiClient["reviseSavedPlan"]>
>["dimension_change"];

export function ProjectEditorPage({ projectId }: ProjectEditorPageProps) {
  const api = useMemo(
    () =>
      new ProjectApiClient(configuredApiBaseUrl(), fetch, browserAccessToken),
    [],
  );
  const [workspace, setWorkspace] = useState<LoadedWorkspace | null>(null);
  const [document, setDocument] = useState<PlanDocument | null>(null);
  const [submitted, setSubmitted] = useState<EditorChangeSet | null>(null);
  const [loading, setLoading] = useState(projectId !== null);
  const [status, setStatus] = useState("Loading project");
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [savingEdits, setSavingEdits] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [savedDimensionChange, setSavedDimensionChange] = useState<{
    readonly projectId: string;
    readonly revisionNumber: number;
    readonly change: DimensionChange;
  } | null>(null);

  async function saveEdits() {
    if (!submitted || !projectId) return;
    setSavingEdits(true);
    setEditError(null);
    try {
      const result = await api.applyEditorCommands(projectId, submitted);
      if (result.revision.parent_revision_id !== submitted.base_revision_id) {
        throw new Error(
          "Saved revision ancestry does not match the editor base.",
        );
      }
      setSubmitted(null);
      setReloadToken((value) => value + 1);
    } catch (cause: unknown) {
      setEditError(
        cause instanceof Error ? cause.message : "Could not save exact edits.",
      );
    } finally {
      setSavingEdits(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    if (projectId === null) {
      setWorkspace(null);
      setDocument(null);
      setLoading(false);
      setStatus("Project not selected");
      setError(null);
      return () => {
        cancelled = true;
      };
    }

    setLoading(true);
    setError(null);
    setStatus("Loading canonical revision");

    void loadProjectWorkspace(api, projectId)
      .then((snapshot) => {
        if (cancelled) {
          return;
        }
        setWorkspace(snapshot);
        setDocument(snapshot.revision?.document ?? null);
        setSubmitted(null);
        setStatus(
          snapshot.revision === null
            ? "No canonical revision yet"
            : `Revision ${String(snapshot.revision.revision_number)} loaded`,
        );
      })
      .catch((caught: unknown) => {
        if (cancelled) {
          return;
        }
        setWorkspace(null);
        setDocument(null);
        setError(
          caught instanceof Error
            ? caught.message
            : "Could not load project workspace.",
        );
        setStatus("Project load failed");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [api, projectId, reloadToken]);

  if (projectId === null) {
    return (
      <main className="page-shell project-editor-shell">
        <section className="editor-empty-project">
          <p className="eyebrow">Project editor</p>
          <h1>Select a project from the dashboard</h1>
          <p className="dashboard-muted">
            The editor requires an explicit project identity and will not open
            demo geometry as a substitute.
          </p>
          <Link className="dashboard-link" href="/">
            ← Back to projects
          </Link>
        </section>
      </main>
    );
  }

  if (loading && workspace === null) {
    return (
      <main className="page-shell project-editor-shell">
        <section className="editor-empty-project">
          Loading authorized project…
        </section>
      </main>
    );
  }

  if (error !== null || workspace === null) {
    return (
      <main className="page-shell project-editor-shell">
        <section className="editor-empty-project editor-error-state">
          <p className="eyebrow">Project editor</p>
          <h1>Could not load this project</h1>
          <p>{error ?? "The project workspace is unavailable."}</p>
          <div className="project-empty-actions">
            <Link className="dashboard-link" href="/">
              ← Back to projects
            </Link>
            <button
              type="button"
              onClick={() => {
                setReloadToken((value) => value + 1);
              }}
            >
              Retry
            </button>
          </div>
        </section>
      </main>
    );
  }

  if (workspace.revision === null || document === null) {
    return (
      <main className="page-shell project-editor-shell">
        <header className="project-editor-header">
          <div>
            <Link className="breadcrumb-link" href="/">
              ← Projects
            </Link>
            <p className="eyebrow">Project workspace</p>
            <h1>{workspace.project.name}</h1>
            <p className="dashboard-muted">{workspace.project.project_id}</p>
          </div>
          <span className="status-pill">No canonical revision</span>
        </header>
        <section className="editor-empty-project">
          <p className="eyebrow">Canonical geometry required</p>
          <h2>This project does not have a PlanDocument revision yet.</h2>
          <p className="dashboard-muted">
            This is intentional. Phase 19.5 removes the demo-fixture fallback
            and refuses to invent plot dimensions, setbacks, floors, rooms,
            doors, or windows. The next plan-setup workflow must collect those
            inputs explicitly before creating revision 1.
          </p>
          <div className="project-empty-actions">
            <Link className="dashboard-link" href="/">
              ← Back to projects
            </Link>
            <button
              type="button"
              onClick={() => {
                setReloadToken((value) => value + 1);
              }}
            >
              Check for revision
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell project-editor-shell">
      <header className="project-editor-header">
        <div>
          <Link className="breadcrumb-link" href="/">
            ← Projects
          </Link>
          <p className="eyebrow">Canonical project editor</p>
          <h1>{workspace.project.name}</h1>
          <p className="dashboard-muted">
            Revision {String(workspace.revision.revision_number)} ·
            millimetre-authoritative geometry
          </p>
        </div>
        <span className="status-pill">{status}</span>
      </header>

      <section className="authority-banner">
        <strong>Authority boundary:</strong> this route is hydrated from project{" "}
        <code>{workspace.project.project_id}</code> revision{" "}
        <code>{workspace.revision.revision_id}</code>. Canvas pixels never
        become authoritative geometry.
      </section>

      <ProjectContextPanel
        project={workspace.project}
        revision={workspace.revision}
        loading={loading}
        status={status}
        onReload={() => {
          setReloadToken((value) => value + 1);
        }}
      />

      <RevisionChatPanel
        key={`chat:${workspace.revision.revision_id}`}
        api={api}
        projectId={workspace.project.project_id}
        baseRevisionId={workspace.revision.revision_id}
        onRevised={(revision, change) => {
          setSavedDimensionChange({
            projectId: revision.project_id,
            revisionNumber: revision.revision_number,
            change,
          });
          setReloadToken((value) => value + 1);
        }}
      />
      {savedDimensionChange?.projectId === workspace.project.project_id ? (
        <p role="status">
          Revision {String(savedDimensionChange.revisionNumber)} saved:{" "}
          {savedDimensionChange.change.room_type}{" "}
          {savedDimensionChange.change.axis.toLowerCase()}{" "}
          {String(savedDimensionChange.change.applied_mm)} mm (requested{" "}
          {String(savedDimensionChange.change.requested_mm)} mm; rounded upward{" "}
          {String(savedDimensionChange.change.rounding_mm)} mm).
        </p>
      ) : null}

      <PlanEditor
        key={document.revision_id}
        document={document}
        onSubmitChangeSet={setSubmitted}
      />

      <RevisionHistoryPanel
        api={api}
        projectId={workspace.project.project_id}
        currentRevisionId={workspace.revision.revision_id}
      />
      <RevisionExportPanel
        key={`exports:${workspace.revision.revision_id}`}
        api={api}
        revision={workspace.revision}
      />

      {submitted === null ? null : (
        <section className="submitted-panel">
          <div className="submitted-heading">
            <div>
              <p className="eyebrow">Staged exact edits</p>
              <h2>
                Change set prepared against revision{" "}
                {submitted.base_revision_id}
              </h2>
            </div>
            <button
              type="button"
              disabled={savingEdits}
              onClick={() => {
                void saveEdits();
              }}
            >
              {savingEdits ? "Saving exact edits..." : "Save exact edits"}
            </button>
          </div>
          <p className="dashboard-muted">
            Save room locks or one exact room dimension at a time. Dimension
            edits regenerate the layout with deterministic validation; other
            edit types are not supported for persistence yet. The prior revision
            stays unchanged.
          </p>
          {editError ? <p role="alert">{editError}</p> : null}
          <pre>{JSON.stringify(submitted, null, 2)}</pre>
        </section>
      )}
    </main>
  );
}
