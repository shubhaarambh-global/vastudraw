"use client";

import Link from "next/link";

import { browserAuthMode } from "../../auth/browser.ts";
import { SaasShell } from "../shell/SaasShell.tsx";

type InfoPageKind = "generation" | "reviews" | "exports" | "settings";

interface WorkspaceInfoPageProps {
  readonly kind: InfoPageKind;
}

const pageCopy: Record<
  InfoPageKind,
  {
    readonly kicker: string;
    readonly title: string;
    readonly description: string;
  }
> = {
  generation: {
    kicker: "Deterministic planning",
    title: "Generation",
    description:
      "Architectural generation is constrained by explicit inputs, solver output, geometry construction, and independent validation.",
  },
  reviews: {
    kicker: "Production policy",
    title: "Vastu reviews",
    description:
      "The production Vastu v1.0 bundle is frozen from explicit human review and source-backed normalized rules.",
  },
  exports: {
    kicker: "Deliverables",
    title: "Exports",
    description:
      "Every supported export is derived from the canonical DrawingScene so output formats cannot silently disagree about geometry.",
  },
  settings: {
    kicker: "Workspace configuration",
    title: "Settings",
    description:
      "Core authority boundaries are explicit: integer millimetres, immutable revisions, deterministic solving, and verified authentication.",
  },
};

function GenerationContent() {
  return (
    <div className="saas-info-grid">
      <section className="saas-card saas-info-main">
        <div className="saas-card-heading">
          <div>
            <p className="saas-kicker">Pipeline</p>
            <h2>Explicit inputs to validated plan</h2>
          </div>
          <span className="saas-status-badge" data-tone="green">
            Deterministic
          </span>
        </div>
        <ol className="saas-step-list">
          <li>
            <span>01</span>
            <div>
              <strong>Project + plot inputs</strong>
              <small>No silent dimensions or inferred site geometry.</small>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <strong>Constraint compilation</strong>
              <small>Hard constraints remain separate from preferences.</small>
            </div>
          </li>
          <li>
            <span>03</span>
            <div>
              <strong>CP-SAT planning</strong>
              <small>Bounded deterministic solver configuration.</small>
            </div>
          </li>
          <li>
            <span>04</span>
            <div>
              <strong>Geometry + validation</strong>
              <small>
                Canonical architecture is independently checked before
                acceptance.
              </small>
            </div>
          </li>
        </ol>
        <Link
          className="saas-link-button saas-link-button-primary"
          href="/projects"
        >
          Choose a project →
        </Link>
      </section>
      <aside className="saas-card">
        <p className="saas-kicker">Current API</p>
        <h2>Architectural generation</h2>
        <p className="saas-muted">
          The generation endpoint is available. The product workflow will
          replace raw request JSON with structured plot, room, and preference
          forms in a later product-input phase.
        </p>
      </aside>
    </div>
  );
}

function ReviewsContent() {
  return (
    <div className="saas-info-grid">
      <section className="saas-card saas-info-main">
        <div className="saas-card-heading">
          <div>
            <p className="saas-kicker">Vastu Specification v1.0</p>
            <h2>Frozen production bundle</h2>
          </div>
          <span className="saas-status-badge" data-tone="green">
            Ready
          </span>
        </div>
        <div className="saas-review-metric">
          <strong>4</strong>
          <span>human-reviewed production rules</span>
        </div>
        <ul className="saas-check-list saas-check-list-large">
          <li>
            <strong>Puja / meditation</strong>
            <span>North-East · centroid-in-zone</span>
          </li>
          <li>
            <strong>Kitchen</strong>
            <span>South-East primary · no inferred North-West fallback</span>
          </li>
          <li>
            <strong>Master bedroom</strong>
            <span>South or South-West</span>
          </li>
          <li>
            <strong>Dedicated bath</strong>
            <span>East · toilet policy remains separate</span>
          </li>
        </ul>
      </section>
      <aside className="saas-card">
        <p className="saas-kicker">Authority</p>
        <h2>Review boundary</h2>
        <p className="saas-muted">
          These rules are SOFT preferences in the MVP. They do not override hard
          architectural, safety, geometry, or feasibility constraints.
        </p>
      </aside>
    </div>
  );
}

function ExportsContent() {
  const formats = [
    ["JPG", "Deterministic raster preview", "Ready"],
    ["PDF", "True vector drawing output", "Ready"],
    ["DXF", "R2018 millimetre CAD exchange", "Ready"],
    ["DWG", "Provider-qualified production backend", "Backend required"],
  ] as const;

  return (
    <section className="saas-card">
      <div className="saas-card-heading">
        <div>
          <p className="saas-kicker">DrawingScene outputs</p>
          <h2>Supported delivery formats</h2>
        </div>
      </div>
      <div className="saas-export-grid">
        {formats.map(([format, description, status]) => (
          <article key={format}>
            <span className="saas-export-format">{format}</span>
            <div>
              <strong>{format} export</strong>
              <p>{description}</p>
            </div>
            <span
              className="saas-status-badge"
              data-tone={status === "Ready" ? "green" : "amber"}
            >
              {status}
            </span>
          </article>
        ))}
      </div>
      <p className="saas-muted saas-section-note">
        Export actions remain project-bound; open a canonical project revision
        before producing deliverables.
      </p>
    </section>
  );
}

function SettingsContent() {
  const mode = browserAuthMode();
  return (
    <div className="saas-info-grid">
      <section className="saas-card saas-info-main">
        <div className="saas-card-heading">
          <div>
            <p className="saas-kicker">Authority settings</p>
            <h2>Production invariants</h2>
          </div>
        </div>
        <dl className="saas-settings-list">
          <div>
            <dt>Canonical units</dt>
            <dd>Integer millimetres (internal authority)</dd>
          </div>
          <div>
            <dt>Display units</dt>
            <dd>Feet + inches (default) or metres</dd>
          </div>
          <div>
            <dt>Plan history</dt>
            <dd>Immutable revisions</dd>
          </div>
          <div>
            <dt>Geometry authority</dt>
            <dd>Server PlanDocument</dd>
          </div>
          <div>
            <dt>Solver mode</dt>
            <dd>Deterministic CP-SAT</dd>
          </div>
          <div>
            <dt>Auth mode</dt>
            <dd>{mode}</dd>
          </div>
        </dl>
      </section>
      <aside className="saas-card">
        <p className="saas-kicker">Safety boundary</p>
        <h2>No silent defaults</h2>
        <p className="saas-muted">
          Missing authoritative geometry stays missing. Browser display pixels,
          display-unit labels, demo fixtures, and unspecified room dimensions
          never become canonical data.
        </p>
      </aside>
    </div>
  );
}

export function WorkspaceInfoPage({ kind }: WorkspaceInfoPageProps) {
  const copy = pageCopy[kind];
  return (
    <SaasShell userLabel="Workspace member">
      <div className="saas-page-heading">
        <div>
          <p className="saas-kicker">{copy.kicker}</p>
          <h1>{copy.title}</h1>
          <p className="saas-muted">{copy.description}</p>
        </div>
      </div>
      {kind === "generation" ? <GenerationContent /> : null}
      {kind === "reviews" ? <ReviewsContent /> : null}
      {kind === "exports" ? <ExportsContent /> : null}
      {kind === "settings" ? <SettingsContent /> : null}
    </SaasShell>
  );
}
