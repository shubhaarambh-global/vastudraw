"use client";

import { useEffect, useMemo, useState } from "react";

import { roomLocked, wallPreview } from "../../editor/document.ts";
import { segmentLengthMm } from "../../editor/math.ts";
import type {
  EditorCommand,
  EditorFloorIndex,
  EditorSelection,
} from "../../editor/types.ts";
import {
  formatLengthMm,
  parseLengthToMm,
  type DisplayLengthUnit,
} from "../../units/length.ts";

interface InspectorPanelProps {
  readonly index: EditorFloorIndex;
  readonly selection: EditorSelection | null;
  readonly commands: readonly EditorCommand[];
  readonly displayUnit: DisplayLengthUnit;
  readonly onStage: (command: EditorCommand) => void;
}

function LengthField(props: {
  readonly label: string;
  readonly valueMm: number | null;
  readonly displayUnit: DisplayLengthUnit;
  readonly minMm?: number;
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
    <label className="numeric-field">
      <span>{props.label}</span>
      <input
        type="text"
        inputMode="decimal"
        value={text}
        onFocus={() => {
          setEditing(true);
        }}
        onChange={(event) => {
          const nextText = event.target.value;
          setText(nextText);
          try {
            const nextMm = parseLengthToMm(nextText, props.displayUnit);
            if (props.minMm !== undefined && nextMm < props.minMm) {
              throw new RangeError(
                `Value must be at least ${formatLengthMm(
                  props.minMm,
                  props.displayUnit,
                )}.`,
              );
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
      <small>
        {props.displayUnit === "ft-in" ? "feet + inches" : "metres"}
        {error ? ` · ${error}` : ""}
      </small>
    </label>
  );
}

export function InspectorPanel(props: InspectorPanelProps) {
  const [wallDelta, setWallDelta] = useState<number | null>(100);
  const [roomTarget, setRoomTarget] = useState<number | null>(3_600);
  const [openingOffset, setOpeningOffset] = useState<number | null>(0);
  const [openingWidth, setOpeningWidth] = useState<number | null>(900);

  const selected = useMemo(() => {
    if (props.selection === null) return null;
    switch (props.selection.kind) {
      case "room":
        return props.index.roomsById.get(props.selection.id) ?? null;
      case "wall":
        return props.index.wallsById.get(props.selection.id) ?? null;
      case "opening":
        return props.index.openingsById.get(props.selection.id) ?? null;
      case "dimension":
        return props.index.dimensionsById.get(props.selection.id) ?? null;
    }
  }, [props.index, props.selection]);

  if (props.selection === null || selected === null) {
    return (
      <aside className="inspector-panel">
        <h2>Inspector</h2>
        <p className="muted">Select a room, wall, opening, or dimension.</p>
        <p className="authority-note">
          Display units are presentation-only. All edit commands remain exact
          integer millimetres.
        </p>
      </aside>
    );
  }

  if (props.selection.kind === "wall") {
    const wall = props.index.wallsById.get(props.selection.id);
    if (wall === undefined) return null;
    const preview = wallPreview(wall, props.commands);
    return (
      <aside className="inspector-panel">
        <h2>Wall</h2>
        <code>{wall.id}</code>
        <dl>
          <dt>Length</dt>
          <dd>
            {formatLengthMm(
              Math.round(segmentLengthMm(preview.start, preview.end)),
              props.displayUnit,
            )}
          </dd>
          <dt>Thickness</dt>
          <dd>{formatLengthMm(wall.thickness_mm, props.displayUnit)}</dd>
        </dl>
        <button
          type="button"
          onClick={() => {
            props.onStage({
              kind: "WALL_LOCK",
              wall_id: wall.id,
              locked: !preview.locked,
            });
          }}
        >
          {preview.locked ? "Unlock wall" : "Lock wall"}
        </button>
        <LengthField
          label="Parallel move"
          valueMm={wallDelta}
          displayUnit={props.displayUnit}
          onChangeMm={setWallDelta}
        />
        <button
          type="button"
          disabled={preview.locked || wallDelta === null}
          onClick={() => {
            if (wallDelta === null) return;
            props.onStage({
              kind: "WALL_MOVE_PARALLEL",
              wall_id: wall.id,
              delta_mm: wallDelta,
            });
          }}
        >
          Stage wall move
        </button>
      </aside>
    );
  }

  if (props.selection.kind === "room") {
    const room = props.index.roomsById.get(props.selection.id);
    if (room === undefined) return null;
    const locked = roomLocked(room.locked ?? false, room.id, props.commands);
    return (
      <aside className="inspector-panel">
        <h2>{room.name ?? room.room_type}</h2>
        <code>{room.id}</code>
        <button
          type="button"
          onClick={() => {
            props.onStage({
              kind: "ROOM_LOCK",
              room_id: room.id,
              locked: !locked,
            });
          }}
        >
          {locked ? "Unlock room" : "Lock room"}
        </button>
        <LengthField
          label="Target dimension"
          valueMm={roomTarget}
          displayUnit={props.displayUnit}
          minMm={1}
          onChangeMm={setRoomTarget}
        />
        <div className="button-row">
          <button
            type="button"
            disabled={locked || roomTarget === null}
            onClick={() => {
              if (roomTarget === null) return;
              props.onStage({
                kind: "ROOM_SET_DIMENSION",
                room_id: room.id,
                axis: "WIDTH",
                target_mm: roomTarget,
              });
            }}
          >
            Stage width
          </button>
          <button
            type="button"
            disabled={locked || roomTarget === null}
            onClick={() => {
              if (roomTarget === null) return;
              props.onStage({
                kind: "ROOM_SET_DIMENSION",
                room_id: room.id,
                axis: "DEPTH",
                target_mm: roomTarget,
              });
            }}
          >
            Stage depth
          </button>
        </div>
        <p className="muted">
          Dimension requests require backend re-solve; the browser does not
          redraw authoritative room geometry.
        </p>
      </aside>
    );
  }

  if (props.selection.kind === "opening") {
    const opening = props.index.openingsById.get(props.selection.id);
    if (opening === undefined) return null;
    return (
      <aside className="inspector-panel">
        <h2>{opening.kind}</h2>
        <code>{opening.id}</code>
        <LengthField
          label="Offset"
          valueMm={openingOffset}
          displayUnit={props.displayUnit}
          minMm={0}
          onChangeMm={setOpeningOffset}
        />
        <button
          type="button"
          disabled={openingOffset === null}
          onClick={() => {
            if (openingOffset === null) return;
            props.onStage({
              kind: "OPENING_MOVE",
              opening_id: opening.id,
              offset_from_wall_start_mm: openingOffset,
            });
          }}
        >
          Stage move
        </button>
        <LengthField
          label="Width"
          valueMm={openingWidth}
          displayUnit={props.displayUnit}
          minMm={1}
          onChangeMm={setOpeningWidth}
        />
        <button
          type="button"
          disabled={openingWidth === null}
          onClick={() => {
            if (openingWidth === null) return;
            props.onStage({
              kind: "OPENING_RESIZE",
              opening_id: opening.id,
              width_mm: openingWidth,
            });
          }}
        >
          Stage resize
        </button>
      </aside>
    );
  }

  return (
    <aside className="inspector-panel">
      <h2>Dimension</h2>
      <code>{props.selection.id}</code>
      <p className="muted">
        Dimensions are derived annotations and are not directly editable.
      </p>
    </aside>
  );
}
