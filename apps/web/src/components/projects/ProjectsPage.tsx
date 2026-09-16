"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { AuthCard } from "../dashboard/AuthCard.tsx";
import { CreateProjectDialog } from "../dashboard/CreateProjectDialog.tsx";
import { useWorkspaceProjects } from "../dashboard/useWorkspaceProjects.ts";
import { SaasShell } from "../shell/SaasShell.tsx";

export function ProjectsPage() {
  const workspace = useWorkspaceProjects();
  const [query, setQuery] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (normalized.length === 0) {
      return workspace.projects;
    }
    return workspace.projects.filter(
      (project) =>
        project.name.toLowerCase().includes(normalized) ||
        project.project_id.toLowerCase().includes(normalized),
    );
  }, [query, workspace.projects]);

  if (workspace.mode === "unconfigured") {
    return (
      <main className="dashboard-shell">
        Authentication configuration required.
      </main>
    );
  }
  if (!workspace.authReady) {
    return <main className="dashboard-shell">Loading secure workspace…</main>;
  }
  if (workspace.mode === "supabase" && !workspace.authenticated) {
    return (
      <main className="dashboard-shell dashboard-auth-shell">
        <AuthCard />
      </main>
    );
  }

  return (
    <SaasShell userLabel={workspace.userLabel}>
      <div className="saas-page-heading">
        <div>
          <p className="saas-kicker">Portfolio</p>
          <h1>Projects</h1>
          <p className="saas-muted">
            Every project owns an immutable revision history and explicit
            canonical geometry.
          </p>
        </div>
        <button
          className="saas-button-primary"
          type="button"
          onClick={() => {
            setCreateOpen(true);
          }}
        >
          + New project
        </button>
      </div>

      <section className="saas-card">
        <div className="saas-project-toolbar">
          <label className="saas-search-field">
            <span aria-hidden="true">⌕</span>
            <input
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
              }}
              placeholder="Search by project name or ID"
              aria-label="Search projects"
            />
          </label>
          <div className="saas-inline-actions">
            <span className="saas-muted saas-small">{workspace.status}</span>
            <button
              type="button"
              disabled={workspace.busy}
              onClick={() => void workspace.refreshProjects()}
            >
              Refresh
            </button>
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="saas-empty-state">
            <strong>
              {workspace.projects.length === 0
                ? "No projects yet"
                : "No matching projects"}
            </strong>
            <span>
              {workspace.projects.length === 0
                ? "Create a project to begin the explicit planning workflow."
                : "Try another project name or identifier."}
            </span>
          </div>
        ) : (
          <div
            className="saas-project-table"
            role="table"
            aria-label="Projects"
          >
            <div className="saas-project-table-head" role="row">
              <span>Project</span>
              <span>Status</span>
              <span>Created</span>
              <span />
            </div>
            {filtered.map((project) => (
              <div
                className="saas-project-table-row"
                role="row"
                key={project.project_id}
              >
                <div className="saas-project-cell-main">
                  <span className="saas-project-monogram">
                    {project.name.slice(0, 1).toUpperCase()}
                  </span>
                  <div>
                    <strong>{project.name}</strong>
                    <code>{project.project_id}</code>
                  </div>
                </div>
                <span
                  className="saas-status-badge"
                  data-tone={
                    project.current_revision_number > 0 ? "green" : "blue"
                  }
                >
                  {project.current_revision_number > 0
                    ? `Revision ${String(project.current_revision_number)}`
                    : "Awaiting canonical plan"}
                </span>
                <span className="saas-muted saas-small">
                  {project.created_at.slice(0, 10)}
                </span>
                <Link
                  className="saas-link-button"
                  href={`/editor?project=${encodeURIComponent(project.project_id)}`}
                >
                  Open →
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>

      <CreateProjectDialog
        open={createOpen}
        busy={workspace.busy}
        onClose={() => {
          setCreateOpen(false);
        }}
        onCreate={async (name) => {
          await workspace.createProject(name);
        }}
      />
    </SaasShell>
  );
}
