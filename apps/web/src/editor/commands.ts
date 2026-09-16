import type { PlanDocument } from "@ai-vastu/contracts";

import { assertSafeIntegerMm } from "./math.ts";
import {
  EDITOR_PROTOCOL_VERSION,
  type EditorChangeSet,
  type EditorCommand,
} from "./types.ts";

function assertNonEmptyId(value: string, label: string): void {
  if (value.trim().length === 0) {
    throw new TypeError(`${label} must not be empty.`);
  }
}

export function validateEditorCommand(command: EditorCommand): EditorCommand {
  switch (command.kind) {
    case "ROOM_LOCK":
      assertNonEmptyId(command.room_id, "room_id");
      return command;
    case "WALL_LOCK":
      assertNonEmptyId(command.wall_id, "wall_id");
      return command;
    case "WALL_MOVE_PARALLEL":
      assertNonEmptyId(command.wall_id, "wall_id");
      assertSafeIntegerMm(command.delta_mm, "delta_mm");
      return command;
    case "ROOM_SET_DIMENSION":
      assertNonEmptyId(command.room_id, "room_id");
      assertSafeIntegerMm(command.target_mm, "target_mm");
      if (command.target_mm <= 0) {
        throw new RangeError("target_mm must be positive.");
      }
      return command;
    case "OPENING_MOVE":
      assertNonEmptyId(command.opening_id, "opening_id");
      assertSafeIntegerMm(
        command.offset_from_wall_start_mm,
        "offset_from_wall_start_mm",
      );
      if (command.offset_from_wall_start_mm < 0) {
        throw new RangeError("Opening offset must be non-negative.");
      }
      return command;
    case "OPENING_RESIZE":
      assertNonEmptyId(command.opening_id, "opening_id");
      assertSafeIntegerMm(command.width_mm, "width_mm");
      if (command.width_mm <= 0) {
        throw new RangeError("Opening width must be positive.");
      }
      return command;
  }
}

export function buildChangeSet(
  document: PlanDocument,
  commands: readonly EditorCommand[],
): EditorChangeSet {
  return {
    protocol_version: EDITOR_PROTOCOL_VERSION,
    project_id: document.project_id,
    base_revision_id: document.revision_id,
    commands: commands.map(validateEditorCommand),
  };
}
