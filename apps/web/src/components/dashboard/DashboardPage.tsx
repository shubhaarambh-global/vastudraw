"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { SaasShell } from "../shell/SaasShell.tsx";
import { AuthCard } from "./AuthCard.tsx";
import { CreateProjectDialog } from "./CreateProjectDialog.tsx";
import { useWorkspaceProjects } from "./useWorkspaceProjects.ts";

function SetupState() {
  return (
    <main className="dashboard-shell dashboard-auth-shell">
      <section className="setup-card">
        <p className="eyebrow">Vastudraw</p>
        <h2>Secure workspace setup</h2>
        <p className="dashboard-muted">
          Choose development bearer mode for local work or Supabase Auth for
          production.
        </p>
      </section>
    </main>
  );
}

export function DashboardPage() {
  const workspace = useWorkspaceProjects();
  const [createOpen, setCreateOpen] = useState(false);

  const withRevisions = useMemo(
    () =>
      workspace.projects.filter(
        (project) => project.current_revision_number > 0,
      ),
    [workspace.projects],
  );
  const awaitingPlan = workspace.projects.length - withRevisions.length;
  const featured = withRevisions[0] ?? workspace.projects[0] ?? null;

  if (workspace.mode === "unconfigured") {
    return <SetupState />;
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
          <p className="saas-kicker">Workspace overview</p>
          <h1>Dashboard</h1>
          <p className="saas-muted">
            Plan, review, and manage canonical residential layouts from one
            deterministic workspace.
          </p>
        </div>
        <div className="saas-page-actions">
          {workspace.mode === "development" ? (
            <span className="saas-dev-pill">Local auth · development</span>
          ) : null}
          {workspace.mode === "supabase" ? (
            <button type="button" onClick={() => void workspace.signOut()}>
              Sign out
            </button>
          ) : null}
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
      </div>

      <section className="saas-stat-grid" aria-label="Workspace summary">
        <article className="saas-stat-card">
          <span className="saas-stat-icon">P</span>
          <div>
            <strong>{String(workspace.projects.length)}</strong>
            <span>Total projects</span>
          </div>
        </article>
        <article className="saas-stat-card">
          <span className="saas-stat-icon saas-stat-icon-blue">R</span>
          <div>
            <strong>{String(withRevisions.length)}</strong>
            <span>With revisions</span>
          </div>
        </article>
        <article className="saas-stat-card">
          <span className="saas-stat-icon saas-stat-icon-amber">A</span>
          <div>
            <strong>{String(awaitingPlan)}</strong>
            <span>Awaiting canonical plan</span>
          </div>
        </article>
        <article className="saas-stat-card">
          <span className="saas-stat-icon saas-stat-icon-green">V1</span>
          <div>
            <strong>Ready</strong>
            <span>Production Vastu bundle</span>
          </div>
        </article>
      </section>

      <div className="saas-dashboard-grid">
        <section className="saas-card saas-feature-card">
          <div className="saas-card-heading">
            <div>
              <p className="saas-kicker">Featured workspace</p>
              <h2>{featured?.name ?? "Create your first project"}</h2>
            </div>
            {featured === null ? null : (
              <span
                className="saas-status-badge"
                data-tone={
                  featured.current_revision_number > 0 ? "green" : "blue"
                }
              >
                {featured.current_revision_number > 0
                  ? `Revision ${String(featured.current_revision_number)}`
                  : "Awaiting canonical plan"}
              </span>
            )}
          </div>

          {featured === null ? (
            <div className="saas-feature-empty">
              <div className="saas-compass-mark" aria-hidden="true">
                N
              </div>
              <div>
                <p className="saas-muted">
                  Start with a project identity. Plot geometry and room
                  requirements are collected explicitly before revision 1 is
                  created.
                </p>
                <button
                  className="saas-button-primary"
                  type="button"
                  onClick={() => {
                    setCreateOpen(true);
                  }}
                >
                  Create project
                </button>
              </div>
            </div>
          ) : (
            <div className="saas-feature-body">
              <div className="saas-feature-copy">
                <p className="saas-muted">
                  {featured.current_revision_number > 0
                    ? "Canonical geometry is available and can be opened in the millimetre-authoritative editor."
                    : "This project is intentionally empty until explicit canonical geometry is supplied."}
                </p>
                <dl className="saas-detail-list">
                  <div>
                    <dt>Project ID</dt>
                    <dd>
                      <code>{featured.project_id}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Created</dt>
                    <dd>{featured.created_at.slice(0, 10)}</dd>
                  </div>
                  <div>
                    <dt>Current revision</dt>
                    <dd>
                      {featured.current_revision_number === 0
                        ? "None"
                        : String(featured.current_revision_number)}
                    </dd>
                  </div>
                </dl>
                <div className="saas-inline-actions">
                  <Link
                    className="saas-link-button saas-link-button-primary"
                    href={`/editor?project=${encodeURIComponent(featured.project_id)}`}
                  >
                    {featured.current_revision_number > 0
                      ? "Open project"
                      : "Open setup"}{" "}
                    →
                  </Link>
                  <Link className="saas-link-button" href="/projects">
                    View all projects
                  </Link>
                </div>
              </div>
              <div
                className="saas-feature-visual"
                aria-label="Deterministic planning status"
              >
                <div className="saas-plan-grid" aria-hidden="true">
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
                <div className="saas-feature-visual-copy">
                  <strong>Canonical-first planning</strong>
                  <span>No demo geometry · integer millimetres</span>
                </div>
              </div>
            </div>
          )}
        </section>

        <aside className="saas-card saas-vastu-card">
          <div className="saas-card-heading">
            <div>
              <p className="saas-kicker">Production rules</p>
              <h2>Vastu v1.0</h2>
            </div>
            <span className="saas-status-badge" data-tone="green">
              Frozen
            </span>
          </div>
          <div className="saas-vastu-ready">
            <span className="saas-ready-ring">4</span>
            <div>
              <strong>Reviewed rules</strong>
              <span>Human-approved production bundle</span>
            </div>
          </div>
          <ul className="saas-check-list">
            <li>Puja / meditation · North-East</li>
            <li>Kitchen · South-East primary</li>
            <li>Master bedroom · South / South-West</li>
            <li>Dedicated bath · East</li>
          </ul>
          <Link className="saas-text-link" href="/reviews">
            Review production policy →
          </Link>
        </aside>
      </div>

      <div className="saas-dashboard-lower">
        <section className="saas-card">
          <div className="saas-card-heading">
            <div>
              <p className="saas-kicker">Your workspace</p>
              <h2>Recent projects</h2>
              <span className="saas-muted saas-small">{workspace.status}</span>
            </div>
            <div className="saas-inline-actions">
              <button
                type="button"
                disabled={workspace.busy}
                onClick={() => void workspace.refreshProjects()}
              >
                Refresh
              </button>
              <Link className="saas-text-link" href="/projects">
                View all →
              </Link>
            </div>
          </div>

          {workspace.projects.length === 0 ? (
            <div className="saas-empty-row">
              No projects yet. Create your first project to begin.
            </div>
          ) : (
            <div className="saas-project-list">
              {workspace.projects.slice(0, 5).map((project) => (
                <Link
                  className="saas-project-row"
                  key={project.project_id}
                  href={`/editor?project=${encodeURIComponent(project.project_id)}`}
                >
                  <span className="saas-project-monogram">
                    {project.name.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="saas-project-row-copy">
                    <strong>{project.name}</strong>
                    <code>{project.project_id}</code>
                  </span>
                  <span
                    className="saas-status-badge"
                    data-tone={
                      project.current_revision_number > 0 ? "green" : "blue"
                    }
                  >
                    {project.current_revision_number > 0
                      ? `Revision ${String(project.current_revision_number)}`
                      : "Awaiting plan"}
                  </span>
                  <span className="saas-project-date">
                    {project.created_at.slice(0, 10)}
                  </span>
                  <span className="saas-project-chevron">›</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <aside className="saas-card">
          <div className="saas-card-heading">
            <div>
              <p className="saas-kicker">Shortcuts</p>
              <h2>Quick actions</h2>
            </div>
          </div>
          <div className="saas-quick-grid">
            <button
              type="button"
              onClick={() => {
                setCreateOpen(true);
              }}
            >
              <span>＋</span>
              <div>
                <strong>New project</strong>
                <small>Create an empty workspace</small>
              </div>
            </button>
            <Link href="/generation">
              <span>⚡</span>
              <div>
                <strong>Generation</strong>
                <small>Review deterministic pipeline</small>
              </div>
            </Link>
            <Link href="/reviews">
              <span>✓</span>
              <div>
                <strong>Vastu review</strong>
                <small>Inspect production rules</small>
              </div>
            </Link>
            <Link href="/exports">
              <span>⇧</span>
              <div>
                <strong>Exports</strong>
                <small>JPG · PDF · DXF</small>
              </div>
            </Link>
          </div>
        </aside>
      </div>

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
