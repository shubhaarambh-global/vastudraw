"use client";

import { useMemo, useState } from "react";

type UnitMode = "FT" | "M";
type Direction = "N" | "E" | "S" | "W";
type PlanningMode = "practical" | "balanced" | "vastu_forward";

interface WizardState {
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
  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>({
    unit: "FT",
    length: "",
    breadth: "",
    north: "N",
    road: "E",
    entrance: "",
    bedrooms: 2,
    bathrooms: 2,
    parking: 1,
    kitchen: "closed",
    dining: "combined",
    puja: 1,
    notes: "",
    planningMode: "balanced",
  });

  const dimensionsValid = useMemo(
    () => Number(state.length) > 0 && Number(state.breadth) > 0,
    [state.breadth, state.length],
  );

  const canContinue = step !== 0 || dimensionsValid;

  function update(patch: Partial<WizardState>) {
    setState((current) => ({ ...current, ...patch }));
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
            <p className="saas-muted">Define the confirmed plot envelope.</p>

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
                  placeholder="30"
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
                  placeholder="50"
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
              Vastu-AI never silently treats them as the same thing.
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
              Commercial V1 currently generates one floor deterministically.
              Multi-floor planning will be enabled in a future architecture
              phase.
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
                <span>Visible roadmap capability; not silently simulated.</span>
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
              Define residential spaces without forcing the client through a
              technical CAD form.
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

            <button type="button" className="phase26c-add-room">
              + Add room
            </button>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="phase26c-step-card">
            <p className="saas-kicker">Step 5 of 6</p>
            <h2>Design intent</h2>
            <p className="saas-muted">
              Add adjacency, privacy, daylight, wardrobe, ventilation and
              lifestyle requirements in natural language.
            </p>

            <textarea
              className="phase26c-intent"
              value={state.notes}
              onChange={(event) => {
                update({ notes: event.target.value });
              }}
              placeholder="Example: Kitchen directly connected to dining. Parents bedroom near entrance. No toilet door visible from living. Wardrobes in all bedrooms. Keep good cross ventilation."
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
                      update({ planningMode: value as PlanningMode });
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
              Phase 26C.2 will send this confirmed brief into the deterministic
              multi-candidate engine.
            </p>

            <dl className="phase26c-review-grid">
              <div>
                <dt>Plot</dt>
                <dd>
                  {state.length || "—"} × {state.breadth || "—"} {state.unit}
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
                <dt>Parking</dt>
                <dd>{String(state.parking)}</dd>
              </div>
              <div>
                <dt>Puja</dt>
                <dd>{String(state.puja)}</dd>
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
              <strong>Candidate set</strong>
              <span>Compact</span>
              <span>Privacy-first</span>
              <span>Daylight</span>
              <span>Circulation</span>
              <span>Vastu-aware</span>
              <span>Alternate zoning</span>
            </div>

            <button type="button" className="phase26c-generate-button" disabled>
              Generate alternatives — enabled in 26C.2
            </button>
          </div>
        ) : null}
      </div>

      <footer className="phase26c-wizard-footer">
        <button
          type="button"
          className="phase26c-back"
          disabled={step === 0}
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
            disabled={!canContinue}
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
