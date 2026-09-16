import type {
  Floor,
  IntPoint,
  Opening,
  PlanDocument,
  Wall,
} from "@ai-vastu/contracts";

import { assertSafeIntegerMm, pointAlongSegment } from "./math.ts";
import type {
  EditorCommand,
  EditorFloorIndex,
  OpeningPreview,
  WallPreview,
} from "./types.ts";

export function activeFloor(
  document: PlanDocument,
  floorId: string | null,
): Floor {
  const floor =
    floorId === null
      ? document.floors[0]
      : document.floors.find((item) => item.id === floorId);
  if (floor === undefined) {
    throw new RangeError("PlanDocument does not contain the requested floor.");
  }
  return floor;
}

export function indexFloor(floor: Floor): EditorFloorIndex {
  return {
    floor,
    roomsById: new Map((floor.rooms ?? []).map((item) => [item.id, item])),
    wallsById: new Map((floor.walls ?? []).map((item) => [item.id, item])),
    openingsById: new Map(
      (floor.openings ?? []).map((item) => [item.id, item]),
    ),
    dimensionsById: new Map(
      (floor.dimensions ?? []).map((item) => [item.id, item]),
    ),
  };
}

function moveWallAxis(
  wall: Wall,
  deltaMm: number,
): { start: IntPoint; end: IntPoint } {
  assertSafeIntegerMm(deltaMm, "wall delta");
  const { start, end } = wall.axis;
  if (start.x_mm === end.x_mm) {
    return {
      start: { x_mm: start.x_mm + deltaMm, y_mm: start.y_mm },
      end: { x_mm: end.x_mm + deltaMm, y_mm: end.y_mm },
    };
  }
  if (start.y_mm === end.y_mm) {
    return {
      start: { x_mm: start.x_mm, y_mm: start.y_mm + deltaMm },
      end: { x_mm: end.x_mm, y_mm: end.y_mm + deltaMm },
    };
  }
  throw new RangeError(
    "Phase 12 preview only supports orthogonal canonical wall axes.",
  );
}

export function wallPreview(
  wall: Wall,
  commands: readonly EditorCommand[],
): WallPreview {
  let start = wall.axis.start;
  let end = wall.axis.end;
  let pending = false;
  let locked = false;
  for (const command of commands) {
    if (command.kind === "WALL_LOCK" && command.wall_id === wall.id) {
      locked = command.locked;
    }
    if (command.kind === "WALL_MOVE_PARALLEL" && command.wall_id === wall.id) {
      const moved = moveWallAxis(
        { ...wall, axis: { start, end } },
        command.delta_mm,
      );
      start = moved.start;
      end = moved.end;
      pending = true;
    }
  }
  return { wall, start, end, pending, locked };
}

export function openingPreview(
  opening: Opening,
  commands: readonly EditorCommand[],
): OpeningPreview {
  let offsetMm = opening.offset_from_wall_start_mm;
  let widthMm = opening.width_mm;
  let pending = false;
  for (const command of commands) {
    if (command.kind === "OPENING_MOVE" && command.opening_id === opening.id) {
      offsetMm = command.offset_from_wall_start_mm;
      pending = true;
    }
    if (
      command.kind === "OPENING_RESIZE" &&
      command.opening_id === opening.id
    ) {
      widthMm = command.width_mm;
      pending = true;
    }
  }
  return { opening, offsetMm, widthMm, pending };
}

export function openingEndpoints(
  wall: WallPreview,
  opening: OpeningPreview,
): { readonly start: IntPoint; readonly end: IntPoint } {
  return {
    start: pointAlongSegment(wall.start, wall.end, opening.offsetMm),
    end: pointAlongSegment(
      wall.start,
      wall.end,
      opening.offsetMm + opening.widthMm,
    ),
  };
}

export function roomLocked(
  canonicalLocked: boolean,
  roomId: string,
  commands: readonly EditorCommand[],
): boolean {
  let locked = canonicalLocked;
  for (const command of commands) {
    if (command.kind === "ROOM_LOCK" && command.room_id === roomId) {
      locked = command.locked;
    }
  }
  return locked;
}
