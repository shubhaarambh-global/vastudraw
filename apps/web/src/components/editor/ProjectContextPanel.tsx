"use client";

import type { ProjectRecord, RevisionRecord } from "../../api/client.ts";

interface ProjectContextPanelProps {
  readonly project: ProjectRecord;
  readonly revision: RevisionRecord;
  readonly loading: boolean;
  readonly status: string;
  readonly onReload: () => void;
}

export function ProjectContextPanel(props: ProjectContextPanelProps) {
  return (
    <section
      className="project-context-panel"
      aria-label="Project revision context"
    >
      <div className="project-context-copy">
        <p className="eyebrow">Canonical project context</p>
        <h2>{props.project.name}</h2>
        <p className="dashboard-muted">
          Revision {String(props.revision.revision_number)} is loaded from the
          authorized project repository. The editor never substitutes demo
          geometry for a project route.
        </p>
      </div>
      <div className="project-context-meta">
        <div>
          <span>Project</span>
          <code>{props.project.project_id}</code>
        </div>
        <div>
          <span>Revision</span>
          <code>{props.revision.revision_id}</code>
        </div>
        <div className="project-context-actions">
          <span className="status-pill">{props.status}</span>
          <button
            type="button"
            disabled={props.loading}
            onClick={props.onReload}
          >
            Reload revision
          </button>
        </div>
      </div>
    </section>
  );
}
