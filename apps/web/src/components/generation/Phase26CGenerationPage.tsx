"use client";

import { useState } from "react";

import { useWorkspaceProjects } from "../dashboard/useWorkspaceProjects.ts";
import { SaasShell } from "../shell/SaasShell.tsx";
import { GenerationWorkspacePage } from "./GenerationWorkspacePage.tsx";
import { Phase26CProjectWizard } from "./Phase26CProjectWizard.tsx";

type EntryMode = "choose" | "new" | "existing";

type Phase26CGenerationPageProps = {
  readonly initialMode?: EntryMode;
};

export function Phase26CGenerationPage({
  initialMode = "choose",
}: Phase26CGenerationPageProps) {
  const workspace = useWorkspaceProjects();
  const [mode, setMode] = useState<EntryMode>(initialMode);

  if (mode === "existing") {
    return (
      <div className="phase26c-embedded-existing">
        <button
          className="phase26c-return-button"
          type="button"
          onClick={() => {
            setMode("choose");
          }}
        >
          ← New project options
        </button>
        <GenerationWorkspacePage />
      </div>
    );
  }

  return (
    <SaasShell
      userLabel={workspace.userLabel}
      contentClassName="phase26c-content"
    >
      {mode === "choose" ? (
        <section className="phase26c-entry">
          <div className="phase26c-entry-heading">
            <p className="saas-kicker">Vastudraw studio</p>
            <h1>Start a project</h1>
            <p className="saas-muted">
              Generate a new residential plan or analyze an existing plan in the
              same project workflow.
            </p>
          </div>

          <div className="phase26c-entry-grid">
            <button
              type="button"
              onClick={() => {
                setMode("new");
              }}
            >
              <span className="phase26c-entry-icon">+</span>
              <strong>Generate new plan</strong>
              <small>
                Start from plot, orientation, spaces and design intent.
              </small>
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("existing");
              }}
            >
              <span className="phase26c-entry-icon">↥</span>
              <strong>Analyze my plan</strong>
              <small>
                JPG · PNG · PDF · DXF · DWG → Vastu audit and later
                same-envelope alternatives.
              </small>
            </button>
          </div>

          <p className="phase26c-v2-note">
            Structural design is intentionally outside V1 and is planned for V2.
          </p>
        </section>
      ) : (
        <>
          <button
            className="phase26c-return-button"
            type="button"
            onClick={() => {
              setMode("choose");
            }}
          >
            ← Project type
          </button>
          <Phase26CProjectWizard />
        </>
      )}
    </SaasShell>
  );
}
