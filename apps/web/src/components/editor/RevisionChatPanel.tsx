"use client";

import { useState } from "react";
import {
  ProjectApiClient,
  type RevisionRecord,
  type DimensionChangeSummary,
} from "../../api/client.ts";

export function RevisionChatPanel(props: {
  readonly api: ProjectApiClient;
  readonly projectId: string;
  readonly baseRevisionId: string;
  readonly onRevised?: (
    revision: RevisionRecord,
    dimensionChange: DimensionChangeSummary,
  ) => void;
}) {
  const [request, setRequest] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<RevisionRecord | null>(null);
  const [dimensionChange, setDimensionChange] = useState<
    | Awaited<
        ReturnType<ProjectApiClient["reviseSavedPlan"]>
      >["dimension_change"]
    | null
  >(null);
  async function revise() {
    setBusy(true);
    setError(null);
    try {
      const result = await props.api.reviseSavedPlan(
        props.projectId,
        saved?.revision_id ?? props.baseRevisionId,
        request,
      );
      if (
        result.revision.parent_revision_id !==
        (saved?.revision_id ?? props.baseRevisionId)
      ) {
        throw new Error(
          "Saved revision ancestry did not match the requested base.",
        );
      }
      setSaved(result.revision);
      setDimensionChange(result.dimension_change);
      setRequest("");
      props.onRevised?.(result.revision, result.dimension_change);
    } catch (cause: unknown) {
      setError(
        cause instanceof Error ? cause.message : "Revision request failed.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="submitted-panel" aria-label="Revision chat">
      <h2>Revise the saved plan</h2>
      <p>
        Local development: increase one uniquely named room width or depth by up
        to 3 metres. The plan is regenerated from saved requirements and the
        previous revision stays available. All rooms may move during
        regeneration.
      </p>
      <p>
        Requests round upward to the plan's dimension precision when needed
        (currently 10 mm / 1 cm). A 305 mm increase on this grid becomes 310 mm.
        The resulting width or depth must match the rounded target exactly;
        infeasible changes are rejected.
      </p>
      <label>
        Room dimension change
        <input
          value={request}
          maxLength={2000}
          disabled={busy}
          placeholder="Make dining 1 ft wider"
          onChange={(event) => {
            setRequest(event.target.value);
          }}
        />
      </label>
      <button
        type="button"
        disabled={busy || !request.trim()}
        onClick={() => {
          void revise();
        }}
      >
        {busy ? "Generating revision..." : "Save revised plan"}
      </button>
      {error ? <p role="alert">{error}</p> : null}
      {saved ? (
        <p role="status">
          Revision {String(saved.revision_number)} saved.{" "}
          {dimensionChange ? (
            <>
              {dimensionChange.room_type} {dimensionChange.axis.toLowerCase()}:
              requested {String(dimensionChange.requested_mm)} mm, applied{" "}
              {String(dimensionChange.applied_mm)} mm (previously{" "}
              {String(dimensionChange.previous_mm)} mm; rounded upward{" "}
              {String(dimensionChange.rounding_mm)} mm).
            </>
          ) : null}{" "}
          <a href={`/editor?project=${encodeURIComponent(props.projectId)}`}>
            Open revised plan
          </a>
        </p>
      ) : null}
    </section>
  );
}
