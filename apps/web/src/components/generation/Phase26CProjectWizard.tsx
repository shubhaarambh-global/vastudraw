"use client";

import { useMemo, useState } from "react";

import {
  configuredApiBaseUrl,
  type AlternativePreviewResponse,
  type ConfirmedRequirementsInput,
  type ConfirmedRoomRequirementInput,
  ProjectApiClient,
} from "../../api/client.ts";
import { browserAccessToken } from "../../auth/browser.ts";
import { Phase26CCandidateWorkspace } from "./Phase26CCandidateWorkspace.tsx";

type UnitMode = "FT" | "M";
type Direction = "N" | "E" | "S" | "W";
type PlanningMode = "practical" | "balanced" | "vastu_forward";

interface CustomRoom {
  readonly id: string;
  readonly roomType: string;
  readonly label: string;
  readonly quantity: number;
}

interface WizardState {
  readonly projectName: string;
  readonly unit: UnitMode;
  readonly length: string;
  readonly breadth: string;
  readonly north: Direction;
  readonly road: Direction;
  readonly entrance: Direction | "";
  readonly bedrooms: number;
  readonly bathrooms: number;
  readonly parking: number;
  readonly kitchen: "open" | "closed";
  readonly dining: "combined" | "separate" | "none";
  readonly puja: number;
  readonly customRooms: readonly CustomRoom[];
  readonly notes: string;
  readonly planningMode: PlanningMode;
}

const STEP_LABELS = [
  "Plot",
  "Orientation",
  "Floors",
  "Spaces",
  "Design intent",
  "Review",
] as const;

const DIRECTIONS: readonly Direction[] = ["N", "E", "S", "W"];

const CUSTOM_ROOM_OPTIONS = [
  ["study", "Study"],
  ["utility", "Utility"],
  ["store", "Store"],
  ["family_lounge", "Family lounge"],
  ["servant_room", "Servant room"],
  ["laundry", "Laundry"],
] as const;

function dimensionToMm(value: string, unit: UnitMode): number {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) {
    throw new RangeError("Plot dimensions must be positive numbers.");
  }
  return Math.round(numeric * (unit === "FT" ? 304.8 : 1000));
}

function northRotation(direction: Direction): number {
  return { N: 0, E: 90, S: 180, W: 270 }[direction];
}

function planningModeToVastuMode(
  mode: PlanningMode,
): "space_efficient" | "balanced" | "strict" {
  if (mode === "practical") return "space_efficient";
  if (mode === "vastu_forward") return "strict";
  return "balanced";
}

function confirmedRooms(state: WizardState): ConfirmedRoomRequirementInput[] {
  const rooms: ConfirmedRoomRequirementInput[] = [
    {
      room_type: "living",
      quantity: 1,
      floor_preference: 0,
      notes: null,
    },
    {
      room_type: "kitchen",
      quantity: 1,
      floor_preference: 0,
      notes:
        state.kitchen === "open"
          ? "Client requested an open kitchen."
          : "Client requested a closed kitchen.",
    },
  ];

  if (state.bedrooms > 0) {
    rooms.push({
      room_type: "bedroom",
      quantity: state.bedrooms,
      floor_preference: 0,
      notes: null,
    });
  }
  if (state.bathrooms > 0) {
    rooms.push({
      room_type: "common_toilet",
      quantity: state.bathrooms,
      floor_preference: 0,
      notes: "Bathroom count confirmed by the client.",
    });
  }
  if (state.dining === "separate") {
    rooms.push({
      room_type: "dining",
      quantity: 1,
      floor_preference: 0,
      notes: "Separate dining room requested.",
    });
  }
  if (state.puja > 0) {
    rooms.push({
      room_type: "puja",
      quantity: state.puja,
      floor_preference: 0,
      notes: null,
    });
  }
  for (const room of state.customRooms) {
    rooms.push({
      room_type: room.roomType,
      quantity: room.quantity,
      floor_preference: 0,
      notes: null,
    });
  }

  return rooms;
}

function buildPrompt(state: WizardState): string {
  const planning =
    state.planningMode === "practical"
      ? "Practical planning balance: architecture 70%, Vastu 30%."
      : state.planningMode === "vastu_forward"
        ? "Vastu-forward planning balance: architecture 30%, Vastu 70%."
        : "Balanced planning: architecture 50%, Vastu 50%.";

  const custom =
    state.customRooms.length === 0
      ? "No additional custom rooms."
      : `Additional rooms: ${state.customRooms
          .map((room) => `${String(room.quantity)} ${room.label}`)
          .join(", ")}.`;

  return [
    `Design a ground-floor Indian residential plan for a ${state.breadth} x ${state.length} ${state.unit === "FT" ? "ft" : "m"} plot.`,
    `True North is ${state.north}; road side is ${state.road}; entrance facing is ${state.entrance || "not specified"}.`,
    `Bedrooms: ${String(state.bedrooms)}. Bathrooms: ${String(state.bathrooms)}. Parking: ${String(state.parking)}.`,
    `Kitchen: ${state.kitchen}. Dining: ${state.dining}. Puja spaces: ${String(state.puja)}.`,
    custom,
    planning,
    state.notes.trim()
      ? `Client design intent: ${state.notes.trim()}`
      : "Use practical circulation, privacy, daylight and ventilation judgement.",
    "Do not sacrifice hard architectural validity for Vastu preferences.",
  ].join("\n");
}

function StepBar({
  step,
  onJump,
}: {
  readonly step: number;
  readonly onJump: (step: number) => void;
}) {
  return (
    <div className="phase26c-progress" aria-label="Project setup progress">
      {STEP_LABELS.map((label, index) => (
        <button
          key={label}
          type="button"
          className="phase26c-progress-step"
          data-state={
            index < step ? "complete" : index === step ? "active" : "future"
          }
          onClick={() => {
            if (index <= step) onJump(index);
          }}
          disabled={index > step}
          aria-current={index === step ? "step" : undefined}
        >
          <span />
          <small>{label}</small>
        </button>
      ))}
    </div>
  );
}

function DirectionPicker({
  label,
  value,
  onChange,
  optional = false,
}: {
  readonly label: string;
  readonly value: Direction | "";
  readonly onChange: (value: Direction | "") => void;
  readonly optional?: boolean;
}) {
  return (
    <fieldset className="phase26c-fieldset">
      <legend>{label}</legend>
      <div className="phase26c-direction-row">
        {optional ? (
          <button
            type="button"
            data-active={value === ""}
            onClick={() => {
              onChange("");
            }}
          >
            Not set
          </button>
        ) : null}
        {DIRECTIONS.map((direction) => (
          <button
            type="button"
            key={direction}
            data-active={value === direction}
            onClick={() => {
              onChange(direction);
            }}
          >
            {direction}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

function Counter({
  label,
  value,
  onChange,
}: {
  readonly label: string;
  readonly value: number;
  readonly onChange: (value: number) => void;
}) {
  return (
    <div className="phase26c-counter">
      <strong>{label}</strong>
      <button
        type="button"
        onClick={() => {
          onChange(Math.max(0, value - 1));
        }}
      >
        −
      </button>
      <span>{String(value)}</span>
      <button
        type="button"
        onClick={() => {
          onChange(Math.min(20, value + 1));
        }}
      >
        +
      </button>
    </div>
  );
}

export function Phase26CProjectWizard() {
  const api = useMemo(
    () =>
      new ProjectApiClient(configuredApiBaseUrl(), fetch, browserAccessToken),
    [],
  );
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [projectId, setProjectId] = useState<string | null>(null);
  const [draftId, setDraftId] = useState<string | null>(null);
  const [preview, setPreview] = useState<AlternativePreviewResponse | null>(
    null,
  );
  const [customRoomType, setCustomRoomType] = useState("study");
  const [state, setState] = useState<WizardState>({
    projectName: "",
    unit: "FT",
    length: "",
    breadth: "",
    north: "N",
    road: "E",
    entrance: "",
    bedrooms: 2,
    bathrooms: 1,
    parking: 1,
    kitchen: "closed",
    dining: "combined",
    puja: 1,
    customRooms: [],
    notes: "",
    planningMode: "balanced",
  });

  const dimensionsValid = useMemo(
    () =>
      Number(state.length) > 0 &&
      Number(state.breadth) > 0 &&
      state.projectName.trim().length > 0,
    [state.breadth, state.length, state.projectName],
  );

  const canContinue = step !== 0 || dimensionsValid;

  function update(patch: Partial<WizardState>) {
    setState((current) => ({ ...current, ...patch }));
    setDraftId(null);
    setPreview(null);
    setStatus("");
  }

  function addCustomRoom() {
    const option = CUSTOM_ROOM_OPTIONS.find(
      ([value]) => value === customRoomType,
    );
    if (!option) return;

    const existing = state.customRooms.find(
      (room) => room.roomType === option[0],
    );
    if (existing) {
      update({
        customRooms: state.customRooms.map((room) =>
          room.id === existing.id
            ? { ...room, quantity: Math.min(20, room.quantity + 1) }
            : room,
        ),
      });
      return;
    }

    update({
      customRooms: [
        ...state.customRooms,
        {
          id: crypto.randomUUID(),
          roomType: option[0],
          label: option[1],
          quantity: 1,
        },
      ],
    });
  }

  async function generateAlternatives() {
    setBusy(true);
    setStatus("Creating project…");

    try {
      const activeProjectId = projectId ?? crypto.randomUUID();
      if (projectId === null) {
        await api.createProject(state.projectName.trim(), activeProjectId);
        setProjectId(activeProjectId);
      }

      const widthMm = dimensionToMm(state.breadth, state.unit);
      const depthMm = dimensionToMm(state.length, state.unit);
      const prompt = buildPrompt(state);

      setStatus("Interpreting the client brief…");
      const interpretation = await api.interpretRequirements(
        activeProjectId,
        prompt,
      );

      const nextDraftId = interpretation.draft.draft_id;
      setDraftId(nextDraftId);

      const confirmation: ConfirmedRequirementsInput = {
        schema_version: "24A.1",
        draft_id: nextDraftId,
        user_id: interpretation.draft.user_id,
        project_id: activeProjectId,
        user_confirmed: true,
        plot_width_mm: widthMm,
        plot_depth_mm: depthMm,
        north_rotation_deg: northRotation(state.north),
        road_side: state.road,
        entrance_facing: state.entrance || null,
        floor_count: 1,
        bedroom_count: state.bedrooms,
        parking_count: state.parking,
        vastu_mode: planningModeToVastuMode(state.planningMode),
        rooms: confirmedRooms(state),
      };

      setStatus("Saving human-confirmed planning inputs…");
      await api.confirmRequirements(nextDraftId, confirmation);

      setStatus("Generating and validating deterministic plan alternatives…");
      const result = await api.generateConfirmedAlternatives(activeProjectId, {
        draft_id: nextDraftId,
        accept_profile_defaults: true,
        max_alternatives: 4,
      });

      setPreview(result);
      setStatus("");
    } catch (cause: unknown) {
      setStatus(
        cause instanceof Error
          ? cause.message
          : "Could not generate plan alternatives.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (preview !== null && projectId !== null && draftId !== null) {
    return (
      <Phase26CCandidateWorkspace
        api={api}
        projectId={projectId}
        draftId={draftId}
        preview={preview}
        onStartOver={() => {
          setProjectId(null);
          setDraftId(null);
          setPreview(null);
          setStep(0);
          setStatus("");
        }}
      />
    );
  }

  return (
    <section className="phase26c-wizard-shell">
      <div className="phase26c-wizard-head">
        <div>
          <p className="saas-kicker">Vastu-AI project setup</p>
          <h1>New residential plan</h1>
          <p className="saas-muted">
            Architecture first, contextual Vastu guidance second. Structural
            planning is reserved for V2.
          </p>
        </div>
        <span className="saas-status-badge" data-tone="blue">
          Step {String(step + 1)} of 6
        </span>
      </div>

      <StepBar step={step} onJump={setStep} />

      <div className="phase26c-wizard-stage">
        {step === 0 ? (
          <div className="phase26c-step-card">
            <p className="saas-kicker">Step 1 of 6</p>
            <h2>Plot</h2>
            <p className="saas-muted">
              Define the project identity and confirmed plot envelope.
            </p>

            <label className="phase26c-project-name">
              <span>Project name</span>
              <input
                value={state.projectName}
                maxLength={200}
                onChange={(event) => {
                  update({ projectName: event.target.value });
                }}
                placeholder="Example: Shah Residence"
              />
            </label>

            <div className="phase26c-unit-toggle">
              {(["FT", "M"] as const).map((unit) => (
                <button
                  type="button"
                  key={unit}
                  data-active={state.unit === unit}
                  onClick={() => {
                    update({ unit });
                  }}
                >
                  {unit}
                </button>
              ))}
            </div>

            <div className="phase26c-dimension-grid">
              <label>
                <span>Length ({state.unit === "FT" ? "feet" : "metres"})</span>
                <input
                  inputMode="decimal"
                  value={state.length}
                  onChange={(event) => {
                    update({ length: event.target.value });
                  }}
                  placeholder="50"
                />
              </label>
              <label>
                <span>Breadth ({state.unit === "FT" ? "feet" : "metres"})</span>
                <input
                  inputMode="decimal"
                  value={state.breadth}
                  onChange={(event) => {
                    update({ breadth: event.target.value });
                  }}
                  placeholder="30"
                />
              </label>
              <div className="phase26c-plot-diagram" aria-hidden="true">
                <span className="phase26c-plot-rect" />
                <small>Confirmed envelope</small>
              </div>
            </div>

            <div className="phase26c-path-note">
              Existing plan? JPG, PNG, PDF, DXF and DWG continue through the
              uploaded-plan audit workflow.
            </div>
          </div>
        ) : null}

        {step === 1 ? (
          <div className="phase26c-step-card">
            <p className="saas-kicker">Step 2 of 6</p>
            <h2>Orientation & access</h2>
            <p className="saas-muted">
              True North, road side and entrance facing are separate facts.
            </p>
            <DirectionPicker
              label="True North"
              value={state.north}
              onChange={(value) => {
                if (value) update({ north: value });
              }}
            />
            <DirectionPicker
              label="Road side"
              value={state.road}
              onChange={(value) => {
                if (value) update({ road: value });
              }}
            />
            <DirectionPicker
              label="Entrance facing"
              value={state.entrance}
              optional
              onChange={(value) => {
                update({ entrance: value });
              }}
            />
          </div>
        ) : null}

        {step === 2 ? (
          <div className="phase26c-step-card">
            <p className="saas-kicker">Step 3 of 6</p>
            <h2>Floors</h2>
            <p className="saas-muted">
              Commercial V1 generates exactly one floor. Multi-floor planning
              remains visible as a future capability and is never silently
              simulated.
            </p>
            <div className="phase26c-locked-option">
              <div>
                <strong>Ground floor</strong>
                <span>Available now</span>
              </div>
              <span className="saas-status-badge" data-tone="green">
                Enabled
              </span>
            </div>
            <div className="phase26c-locked-option" data-disabled="true">
              <div>
                <strong>G + 1 / G + 2 / custom</strong>
                <span>Future deterministic multi-floor architecture.</span>
              </div>
              <span className="saas-status-badge">Future</span>
            </div>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="phase26c-step-card">
            <p className="saas-kicker">Step 4 of 6</p>
            <h2>Spaces & layout</h2>
            <p className="saas-muted">
              Define the residential program without exposing solver internals.
            </p>

            <div className="phase26c-choice-row">
              <strong>Kitchen</strong>
              {(["open", "closed"] as const).map((value) => (
                <button
                  type="button"
                  key={value}
                  data-active={state.kitchen === value}
                  onClick={() => {
                    update({ kitchen: value });
                  }}
                >
                  {value === "open" ? "Open" : "Closed"}
                </button>
              ))}
            </div>

            <div className="phase26c-choice-row">
              <strong>Dining</strong>
              {(["combined", "separate", "none"] as const).map((value) => (
                <button
                  type="button"
                  key={value}
                  data-active={state.dining === value}
                  onClick={() => {
                    update({ dining: value });
                  }}
                >
                  {value[0]?.toUpperCase()}
                  {value.slice(1)}
                </button>
              ))}
            </div>

            <div className="phase26c-counter-grid">
              <Counter
                label="Bedrooms"
                value={state.bedrooms}
                onChange={(bedrooms) => {
                  update({ bedrooms });
                }}
              />
              <Counter
                label="Bathrooms"
                value={state.bathrooms}
                onChange={(bathrooms) => {
                  update({ bathrooms });
                }}
              />
              <Counter
                label="Parking"
                value={state.parking}
                onChange={(parking) => {
                  update({ parking });
                }}
              />
              <Counter
                label="Puja"
                value={state.puja}
                onChange={(puja) => {
                  update({ puja });
                }}
              />
            </div>

            <div className="phase26c-custom-room">
              <select
                value={customRoomType}
                onChange={(event) => {
                  setCustomRoomType(event.target.value);
                }}
                aria-label="Additional room type"
              >
                {CUSTOM_ROOM_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="phase26c-add-room"
                onClick={addCustomRoom}
              >
                + Add room
              </button>
            </div>

            {state.customRooms.length > 0 ? (
              <div className="phase26c-custom-room-list">
                {state.customRooms.map((room) => (
                  <div key={room.id}>
                    <strong>{room.label}</strong>
                    <span>× {String(room.quantity)}</span>
                    <button
                      type="button"
                      onClick={() => {
                        update({
                          customRooms: state.customRooms.filter(
                            (item) => item.id !== room.id,
                          ),
                        });
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {step === 4 ? (
          <div className="phase26c-step-card">
            <p className="saas-kicker">Step 5 of 6</p>
            <h2>Design intent</h2>
            <p className="saas-muted">
              Describe adjacency, privacy, wardrobes, daylight, ventilation and
              lifestyle needs. Phase 26A interprets these as soft architectural
              intent.
            </p>

            <textarea
              className="phase26c-intent"
              value={state.notes}
              onChange={(event) => {
                update({ notes: event.target.value });
              }}
              placeholder="Example: Kitchen directly connected to dining. Parents bedroom near entrance. No toilet door visible from living. Wardrobes in bedrooms. Keep good cross ventilation."
            />

            <fieldset className="phase26c-fieldset">
              <legend>Planning balance</legend>
              <div className="phase26c-mode-grid">
                {[
                  ["practical", "Practical", "Architecture 70% · Vastu 30%"],
                  ["balanced", "Balanced", "Architecture 50% · Vastu 50%"],
                  [
                    "vastu_forward",
                    "Vastu-forward",
                    "Architecture 30% · Vastu 70%",
                  ],
                ].map(([value, label, detail]) => (
                  <button
                    key={value}
                    type="button"
                    data-active={state.planningMode === value}
                    onClick={() => {
                      update({
                        planningMode: value as PlanningMode,
                      });
                    }}
                  >
                    <strong>{label}</strong>
                    <span>{detail}</span>
                  </button>
                ))}
              </div>
            </fieldset>
          </div>
        ) : null}

        {step === 5 ? (
          <div className="phase26c-step-card">
            <p className="saas-kicker">Step 6 of 6</p>
            <h2>Review & generate</h2>
            <p className="saas-muted">
              The confirmed brief passes through requirements confirmation,
              architectural reasoning, soft Vastu reasoning and the
              deterministic candidate engine.
            </p>

            <dl className="phase26c-review-grid">
              <div>
                <dt>Project</dt>
                <dd>{state.projectName || "—"}</dd>
              </div>
              <div>
                <dt>Plot</dt>
                <dd>
                  {state.breadth || "—"} × {state.length || "—"} {state.unit}
                </dd>
              </div>
              <div>
                <dt>True North</dt>
                <dd>{state.north}</dd>
              </div>
              <div>
                <dt>Road side</dt>
                <dd>{state.road}</dd>
              </div>
              <div>
                <dt>Entrance</dt>
                <dd>{state.entrance || "Not set"}</dd>
              </div>
              <div>
                <dt>Bedrooms</dt>
                <dd>{String(state.bedrooms)}</dd>
              </div>
              <div>
                <dt>Bathrooms</dt>
                <dd>{String(state.bathrooms)}</dd>
              </div>
              <div>
                <dt>Planning mode</dt>
                <dd>{state.planningMode.replace("_", " ")}</dd>
              </div>
              <div>
                <dt>Structural</dt>
                <dd>V2 — not included</dd>
              </div>
            </dl>

            <div className="phase26c-candidate-preview">
              <strong>Candidate exploration</strong>
              <span>Space-use search</span>
              <span>Topology search</span>
              <span>Boundary search</span>
              <span>Access search</span>
              <span>Soft Vastu comparison</span>
              <span>Alternate zoning search</span>
            </div>

            <button
              type="button"
              className="phase26c-generate-button"
              disabled={busy}
              onClick={() => {
                void generateAlternatives();
              }}
            >
              {busy ? "Generating alternatives…" : "Generate alternatives"}
            </button>

            {status ? (
              <p className="phase26c3-generation-status">{status}</p>
            ) : null}
          </div>
        ) : null}
      </div>

      <footer className="phase26c-wizard-footer">
        <button
          type="button"
          className="phase26c-back"
          disabled={step === 0 || busy}
          onClick={() => {
            setStep((current) => Math.max(0, current - 1));
          }}
        >
          Back
        </button>
        {step < 5 ? (
          <button
            type="button"
            className="phase26c-next"
            disabled={!canContinue || busy}
            onClick={() => {
              setStep((current) => Math.min(5, current + 1));
            }}
          >
            Next
          </button>
        ) : null}
      </footer>
    </section>
  );
}
