import type {
  Dimension,
  Floor,
  IntPoint,
  Opening,
  PlanDocument,
  RoomGeometry,
  Wall,
} from "@ai-vastu/contracts";

export const EDITOR_PROTOCOL_VERSION = "1.0.0" as const;

export type EditorTool = "select" | "pan";
export type SelectionKind = "room" | "wall" | "opening" | "dimension";

export interface EditorSelection {
  readonly kind: SelectionKind;
  readonly id: string;
}

export interface EditorViewport {
  readonly pixelsPerMm: number;
  readonly originXPx: number;
  readonly originYPx: number;
}

export interface CanvasSize {
  readonly widthPx: number;
  readonly heightPx: number;
}

export interface LayerVisibility {
  readonly grid: boolean;
  readonly rulers: boolean;
  readonly rooms: boolean;
  readonly walls: boolean;
  readonly openings: boolean;
  readonly dimensions: boolean;
  readonly annotations: boolean;
}

export interface SnapSettings {
  readonly enabled: boolean;
  readonly gridMm: number;
}

export interface WorldBounds {
  readonly minXmm: number;
  readonly minYmm: number;
  readonly maxXmm: number;
  readonly maxYmm: number;
}

export interface ScreenPoint {
  readonly xPx: number;
  readonly yPx: number;
}

export interface EditorChangeSet {
  readonly protocol_version: typeof EDITOR_PROTOCOL_VERSION;
  readonly project_id: string;
  readonly base_revision_id: string;
  readonly commands: readonly EditorCommand[];
}

export type EditorCommand =
  | {
      readonly kind: "ROOM_LOCK";
      readonly room_id: string;
      readonly locked: boolean;
    }
  | {
      readonly kind: "WALL_LOCK";
      readonly wall_id: string;
      readonly locked: boolean;
    }
  | {
      readonly kind: "WALL_MOVE_PARALLEL";
      readonly wall_id: string;
      readonly delta_mm: number;
    }
  | {
      readonly kind: "ROOM_SET_DIMENSION";
      readonly room_id: string;
      readonly axis: "WIDTH" | "DEPTH";
      readonly target_mm: number;
    }
  | {
      readonly kind: "OPENING_MOVE";
      readonly opening_id: string;
      readonly offset_from_wall_start_mm: number;
    }
  | {
      readonly kind: "OPENING_RESIZE";
      readonly opening_id: string;
      readonly width_mm: number;
    };

export interface EditorFloorIndex {
  readonly floor: Floor;
  readonly roomsById: ReadonlyMap<string, RoomGeometry>;
  readonly wallsById: ReadonlyMap<string, Wall>;
  readonly openingsById: ReadonlyMap<string, Opening>;
  readonly dimensionsById: ReadonlyMap<string, Dimension>;
}

export interface WallPreview {
  readonly wall: Wall;
  readonly start: IntPoint;
  readonly end: IntPoint;
  readonly pending: boolean;
  readonly locked: boolean;
}

export interface OpeningPreview {
  readonly opening: Opening;
  readonly offsetMm: number;
  readonly widthMm: number;
  readonly pending: boolean;
}

export type CanonicalPlanDocument = PlanDocument;
