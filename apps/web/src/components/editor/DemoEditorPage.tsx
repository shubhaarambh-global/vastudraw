"use client";

import type { PlanDocument } from "@ai-vastu/contracts";
import { useState } from "react";

import { demoDocument } from "../../editor/demo-document.ts";
import type { EditorChangeSet } from "../../editor/types.ts";
import { PlanEditor } from "./PlanEditor.tsx";
import { ProjectWorkflowPanel } from "./ProjectWorkflowPanel.tsx";

export function DemoEditorPage() {
  const [submitted, setSubmitted] = useState<EditorChangeSet | null>(null);
  const [document, setDocument] = useState<PlanDocument>(demoDocument);
  return (
    <main className="page-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">Phase 19 · authenticated project workspace</p>
          <h1>AI Vastu Architect</h1>
          <p>
            Millimetre-native review and exact edit staging over the canonical
            PlanDocument.
          </p>
        </div>
        <div className="status-pill">
          Demo fixture · canonical geometry unchanged
        </div>
      </header>
      <section className="authority-banner">
        <strong>Authority boundary:</strong> Konva is a rendering/input surface
        only. Pixel positions never become authoritative geometry. Exact edits
        are staged as integer-mm commands against revision{" "}
        <code>{document.revision_id}</code>.
      </section>
      <ProjectWorkflowPanel
        document={document}
        onDocumentLoaded={setDocument}
      />
      <PlanEditor
        key={document.revision_id}
        document={document}
        onSubmitChangeSet={setSubmitted}
      />
      {submitted === null ? null : (
        <section className="submitted-panel">
          <h2>Last staged change set</h2>
          <pre>{JSON.stringify(submitted, null, 2)}</pre>
        </section>
      )}
    </main>
  );
}
