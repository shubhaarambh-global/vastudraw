"use client";

import { useEffect, useMemo, useState, type SyntheticEvent } from "react";

import {
  DEFAULT_DISPLAY_LENGTH_UNIT,
  formatLengthMm,
  parseLengthToMm,
  type DisplayLengthUnit,
} from "../../units/length.ts";

type Proposed<T> = {
  value: T;
  source: string;
  confidence: number;
  requires_confirmation: boolean;
};

type Draft = {
  schema_version: "24A.1";
  draft_id: string;
  user_id: string;
  project_id: string;
  prompt: string;
  plot_width_mm: Proposed<number> | null;
  plot_depth_mm: Proposed<number> | null;
  north_rotation_deg: Proposed<number> | null;
  road_side: Proposed<string> | null;
  entrance_facing: Proposed<string> | null;
  floor_count: Proposed<number> | null;
  bedroom_count: Proposed<number> | null;
  parking_count: Proposed<number> | null;
  vastu_mode: string;
  rooms: Array<{
    room_type: string;
    quantity: number;
    floor_preference: number | null;
    notes: string | null;
  }>;
  questions: string[];
  warnings: string[];
  reference_names: string[];
  provider: string;
  model: string | null;
};

const API_BASE =
  process.env.NEXT_PUBLIC_AI_VASTU_API_BASE_URL ?? "http://127.0.0.1:8000";

const inputStyle = {
  width: "100%",
  border: "1px solid #d9ded9",
  borderRadius: "10px",
  padding: "10px 12px",
  background: "#fff",
} as const;

function LengthReviewField(props: {
  readonly label: string;
  readonly valueMm: number | null;
  readonly displayUnit: DisplayLengthUnit;
  readonly onChangeMm: (value: number | null) => void;
}) {
  const [text, setText] = useState(
    props.valueMm === null
      ? ""
      : formatLengthMm(props.valueMm, props.displayUnit),
  );
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) {
      setText(
        props.valueMm === null
          ? ""
          : formatLengthMm(props.valueMm, props.displayUnit),
      );
    }
  }, [editing, props.displayUnit, props.valueMm]);

  return (
    <label>
      {props.label}
      <input
        style={inputStyle}
        type="text"
        inputMode="decimal"
        value={text}
        placeholder={
          props.displayUnit === "ft-in" ? `Example: 30'-6"` : "Example: 9.296 m"
        }
        onFocus={() => {
          setEditing(true);
        }}
        onChange={(event) => {
          const nextText = event.target.value;
          setText(nextText);
          try {
            const nextMm = parseLengthToMm(nextText, props.displayUnit);
            if (nextMm <= 0) {
              throw new RangeError("Dimension must be greater than zero.");
            }
            setError(null);
            props.onChangeMm(nextMm);
          } catch (cause) {
            setError(
              cause instanceof Error ? cause.message : "Invalid length.",
            );
            props.onChangeMm(null);
          }
        }}
        onBlur={() => {
          setEditing(false);
          if (props.valueMm !== null) {
            setText(formatLengthMm(props.valueMm, props.displayUnit));
          }
        }}
      />
      <small style={{ color: error ? "#a12622" : "#667066" }}>
        {props.displayUnit === "ft-in"
          ? "Feet + inches · supports 10'-6 1/2\""
          : "Metres · displayed to 0.001 m"}
        {error ? ` · ${error}` : ""}
      </small>
    </label>
  );
}

export function RequirementsReviewPage() {
  const [projectId, setProjectId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [token, setToken] = useState("dev-local-token");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [displayUnit, setDisplayUnit] = useState<DisplayLengthUnit>(
    DEFAULT_DISPLAY_LENGTH_UNIT,
  );

  const [widthMm, setWidthMm] = useState<number | null>(null);
  const [depthMm, setDepthMm] = useState<number | null>(null);
  const [north, setNorth] = useState("");
  const [road, setRoad] = useState("");
  const [entrance, setEntrance] = useState("");
  const [floors, setFloors] = useState("1");
  const [bedrooms, setBedrooms] = useState("0");
  const [parking, setParking] = useState("0");

  const canConfirm = useMemo(
    () =>
      Boolean(
        draft &&
        widthMm !== null &&
        depthMm !== null &&
        north &&
        road &&
        floors &&
        bedrooms &&
        parking,
      ),
    [draft, widthMm, depthMm, north, road, floors, bedrooms, parking],
  );

  async function interpret(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setStatus("Interpreting client brief…");

    const body = new FormData();
    body.set("project_id", projectId);
    body.set("prompt", prompt);
    for (const file of files) body.append("files", file);

    try {
      const response = await fetch(`${API_BASE}/requirements/interpret`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body,
      });
      const result = (await response.json()) as {
        draft?: Draft;
        detail?: string;
      };
      if (!response.ok || !result.draft) {
        throw new Error(result.detail ?? "Interpretation failed.");
      }
      setDraft(result.draft);
      setWidthMm(result.draft.plot_width_mm?.value ?? null);
      setDepthMm(result.draft.plot_depth_mm?.value ?? null);
      setNorth(String(result.draft.north_rotation_deg?.value ?? ""));
      setRoad(result.draft.road_side?.value ?? "");
      setEntrance(result.draft.entrance_facing?.value ?? "");
      setFloors(String(result.draft.floor_count?.value ?? 1));
      setBedrooms(String(result.draft.bedroom_count?.value ?? 0));
      setParking(String(result.draft.parking_count?.value ?? 0));
      setStatus("Draft ready for human confirmation.");
    } catch (cause) {
      setStatus("");
      setError(
        cause instanceof Error ? cause.message : "Interpretation failed.",
      );
    }
  }

  async function confirm() {
    if (!draft || widthMm === null || depthMm === null) return;
    setError("");
    setStatus("Saving confirmed requirements…");

    const payload = {
      schema_version: "24A.1",
      draft_id: draft.draft_id,
      user_id: draft.user_id,
      project_id: draft.project_id,
      user_confirmed: true,
      plot_width_mm: widthMm,
      plot_depth_mm: depthMm,
      north_rotation_deg: Number(north),
      road_side: road,
      entrance_facing: entrance || null,
      floor_count: Number(floors),
      bedroom_count: Number(bedrooms),
      parking_count: Number(parking),
      vastu_mode: draft.vastu_mode,
      rooms: draft.rooms.map((room) => ({
        room_type: room.room_type,
        quantity: room.quantity,
        floor_preference: room.floor_preference,
        notes: room.notes,
      })),
    };

    try {
      const response = await fetch(
        `${API_BASE}/requirements/drafts/${draft.draft_id}/confirm`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        },
      );
      const result = (await response.json()) as {
        confirmed?: unknown;
        detail?: string;
      };
      if (!response.ok || !result.confirmed) {
        throw new Error(result.detail ?? "Confirmation failed.");
      }
      setStatus(
        "Confirmed. Requirements are ready for deterministic generation.",
      );
    } catch (cause) {
      setStatus("");
      setError(cause instanceof Error ? cause.message : "Confirmation failed.");
    }
  }

  return (
    <main style={{ padding: "30px", maxWidth: "1080px", margin: "0 auto" }}>
      <h1 style={{ marginBottom: "8px" }}>AI Requirements Review</h1>
      <p style={{ color: "#667066", lineHeight: 1.6 }}>
        AI extracts a draft only. Confirm every planning input before the
        deterministic solver may use it.
      </p>

      <form
        onSubmit={(event) => void interpret(event)}
        style={{
          display: "grid",
          gap: "14px",
          padding: "20px",
          border: "1px solid #e1e5e1",
          borderRadius: "16px",
          background: "#fff",
        }}
      >
        <label>
          Project UUID
          <input
            style={inputStyle}
            value={projectId}
            onChange={(event) => {
              setProjectId(event.target.value);
            }}
            required
          />
        </label>
        <label>
          Development bearer token
          <input
            style={inputStyle}
            value={token}
            onChange={(event) => {
              setToken(event.target.value);
            }}
            required
          />
        </label>
        <label>
          Client brief
          <textarea
            style={{ ...inputStyle, minHeight: "130px" }}
            value={prompt}
            onChange={(event) => {
              setPrompt(event.target.value);
            }}
            required
          />
        </label>
        <label>
          JPG / PNG / PDF references
          <input
            style={inputStyle}
            type="file"
            multiple
            accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
            onChange={(event) => {
              setFiles(Array.from(event.target.files ?? []));
            }}
          />
        </label>
        <button type="submit">Interpret requirements</button>
      </form>

      {draft ? (
        <section style={{ marginTop: "22px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "end",
              gap: "16px",
              flexWrap: "wrap",
            }}
          >
            <div>
              <h2>Review extracted values</h2>
              <p style={{ color: "#667066" }}>
                Canonical geometry stays in integer millimetres. Switching
                display units never changes the stored dimensions.
              </p>
            </div>
            <label>
              Display units
              <select
                style={{ ...inputStyle, minWidth: "180px" }}
                value={displayUnit}
                onChange={(event) => {
                  setDisplayUnit(event.target.value as DisplayLengthUnit);
                }}
              >
                <option value="ft-in">Feet &amp; Inches</option>
                <option value="m">Metres</option>
              </select>
            </label>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            <LengthReviewField
              label="Plot width"
              valueMm={widthMm}
              displayUnit={displayUnit}
              onChangeMm={setWidthMm}
            />
            <LengthReviewField
              label="Plot depth"
              valueMm={depthMm}
              displayUnit={displayUnit}
              onChangeMm={setDepthMm}
            />
            {[
              ["North rotation (°)", north, setNorth],
              ["Road side", road, setRoad],
              ["Entrance facing", entrance, setEntrance],
              ["Floor count", floors, setFloors],
              ["Bedroom count", bedrooms, setBedrooms],
              ["Parking count", parking, setParking],
            ].map(([label, value, setter]) => (
              <label key={String(label)}>
                {String(label)}
                <input
                  style={inputStyle}
                  value={String(value)}
                  onChange={(event) => {
                    (setter as (value: string) => void)(event.target.value);
                  }}
                />
              </label>
            ))}
          </div>

          {draft.questions.length ? (
            <>
              <h3>Clarifications required</h3>
              <ul>
                {draft.questions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </>
          ) : null}

          {draft.warnings.length ? (
            <>
              <h3>Warnings</h3>
              <ul>
                {draft.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </>
          ) : null}

          <button
            disabled={!canConfirm}
            onClick={() => {
              void confirm();
            }}
          >
            Confirm requirements
          </button>
        </section>
      ) : null}

      {status ? <p>{status}</p> : null}
      {error ? <p style={{ color: "#a12622" }}>{error}</p> : null}
    </main>
  );
}
