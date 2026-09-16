"use client";

import { useMemo, useState } from "react";

import { roomLocked, wallPreview } from "../../editor/document.ts";
import { segmentLengthMm } from "../../editor/math.ts";
import type {
  EditorCommand,
  EditorFloorIndex,
  EditorSelection,
} from "../../editor/types.ts";

interface InspectorPanelProps {
  readonly index: EditorFloorIndex;
  readonly selection: EditorSelection | null;
  readonly commands: readonly EditorCommand[];
  readonly onStage: (command: EditorCommand) => void;
}

function NumericField(props: {
  readonly label: string;
  readonly value: number;
  readonly min?: number;
  readonly onChange: (value: number) => void;
}) {
  return (
    <label className="numeric-field">
      <span>{props.label}</span>
      <input
        type="number"
        step={1}
        min={props.min}
        value={props.value}
        onChange={(event) => {
          props.onChange(Number(event.target.value));
        }}
      />
      <small>mm</small>
    </label>
  );
}

export function InspectorPanel(props: InspectorPanelProps) {
  const [wallDelta, setWallDelta] = useState(100);
  const [roomTarget, setRoomTarget] = useState(3_600);
  const [openingOffset, setOpeningOffset] = useState(0);
  const [openingWidth, setOpeningWidth] = useState(900);

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
          Canvas pixels are display-only. All edit commands use integer
          millimetres.
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
          <dd>{Math.round(segmentLengthMm(preview.start, preview.end))} mm</dd>
          <dt>Thickness</dt>
          <dd>{wall.thickness_mm} mm</dd>
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
        <NumericField
          label="Parallel move"
          value={wallDelta}
          onChange={setWallDelta}
        />
        <button
          type="button"
          disabled={preview.locked}
          onClick={() => {
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
        <NumericField
          label="Target dimension"
          value={roomTarget}
          min={1}
          onChange={setRoomTarget}
        />
        <div className="button-row">
          <button
            type="button"
            disabled={locked}
            onClick={() => {
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
            disabled={locked}
            onClick={() => {
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
        <NumericField
          label="Offset"
          value={openingOffset}
          min={0}
          onChange={setOpeningOffset}
        />
        <button
          type="button"
          onClick={() => {
            props.onStage({
              kind: "OPENING_MOVE",
              opening_id: opening.id,
              offset_from_wall_start_mm: openingOffset,
            });
          }}
        >
          Stage move
        </button>
        <NumericField
          label="Width"
          value={openingWidth}
          min={1}
          onChange={setOpeningWidth}
        />
        <button
          type="button"
          onClick={() => {
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
        Dimensions are derived annotations in Phase 12 and are not directly
        editable.
      </p>
    </aside>
  );
}
