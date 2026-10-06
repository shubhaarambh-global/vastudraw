"use client";

import { useState } from "react";
import {
  ProjectApiClient,
  type ProductionExportFormat,
  type RevisionRecord,
} from "../../api/client.ts";

export function RevisionExportPanel(props: {
  readonly api: ProjectApiClient;
  readonly revision: RevisionRecord;
}) {
  const [busy, setBusy] = useState<ProductionExportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [floorIndex, setFloorIndex] = useState(
    props.revision.document.floors[0]?.index ?? 0,
  );
  async function download(format: ProductionExportFormat) {
    const revision = props.revision;
    if (!revision.source_candidate_id) return;
    setBusy(format);
    setError(null);
    try {
      const result = await props.api.downloadSelectedExport(
        revision.project_id,
        {
          revision_id: revision.revision_id,
          candidate_id: revision.source_candidate_id,
          format,
          scope: "FLOOR",
          floor_index: floorIndex,
        },
      );
      if (
        result.sourcePlanHash !== revision.plan_document_hash ||
        result.candidateId !== revision.source_candidate_id
      ) {
        throw new Error("The export does not match this saved revision.");
      }
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = result.filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (cause: unknown) {
      setError(
        cause instanceof Error ? cause.message : "Export download failed.",
      );
    } finally {
      setBusy(null);
    }
  }
  return (
    <section className="submitted-panel" aria-label="Saved revision exports">
      <h2>Download saved revision {String(props.revision.revision_number)}</h2>
      {!props.revision.source_candidate_id ? (
        <p>Exports are available for saved generated revisions.</p>
      ) : (
        <>
          {props.revision.document.floors.length > 1 ? (
            <label>
              Export floor
              <select
                value={floorIndex}
                onChange={(event) => {
                  setFloorIndex(Number(event.target.value));
                }}
              >
                {props.revision.document.floors.map((floor) => (
                  <option key={floor.id} value={floor.index}>
                    {floor.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <div className="workflow-actions">
            {(["JPEG", "PDF", "DXF"] as const).map((format) => (
              <button
                key={format}
                type="button"
                disabled={busy !== null}
                onClick={() => {
                  void download(format);
                }}
              >
                {busy === format ? `Preparing ${format}...` : format}
              </button>
            ))}
          </div>
        </>
      )}
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
