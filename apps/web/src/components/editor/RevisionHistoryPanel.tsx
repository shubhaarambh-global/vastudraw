"use client";

import { useEffect, useState } from "react";
import { ProjectApiClient, type RevisionRecord } from "../../api/client.ts";

export function RevisionHistoryPanel(props: {
  readonly api: ProjectApiClient;
  readonly projectId: string;
  readonly currentRevisionId: string;
}) {
  const [revisions, setRevisions] = useState<readonly RevisionRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    void props.api
      .listRevisions(props.projectId)
      .then((items) => {
        if (!cancelled) {
          setRevisions(items);
          setError(null);
        }
      })
      .catch((cause: unknown) => {
        if (!cancelled)
          setError(
            cause instanceof Error
              ? cause.message
              : "Could not load revision history.",
          );
      });
    return () => {
      cancelled = true;
    };
  }, [props.api, props.projectId, props.currentRevisionId]);
  return (
    <section className="submitted-panel" aria-label="Revision history">
      <h2>Revision history</h2>
      {error ? <p role="alert">{error}</p> : null}
      <ol>
        {revisions.map((revision) => (
          <li key={revision.revision_id}>
            <details>
              <summary>
                Revision {String(revision.revision_number)}
                {revision.revision_id === props.currentRevisionId
                  ? " · Current"
                  : ""}
              </summary>
              <p>
                Revision: <code>{revision.revision_id}</code>
              </p>
              <p>
                Parent:{" "}
                <code>{revision.parent_revision_id ?? "First revision"}</code>
              </p>
              <p>
                Canonical hash: <code>{revision.plan_document_hash}</code>
              </p>
            </details>
          </li>
        ))}
      </ol>
    </section>
  );
}
