import type { PlanDocument } from "@ai-vastu/contracts";
import { create } from "zustand";

import { validateEditorCommand } from "./commands.ts";
import { activeFloor } from "./document.ts";
import {
  EMPTY_HISTORY,
  redoCommand,
  stageCommand,
  undoCommand,
  type CommandHistory,
} from "./history.ts";
import {
  fitBoundsToCanvas,
  panViewport,
  polygonBounds,
  zoomAtScreenPoint,
} from "./math.ts";
import type {
  CanvasSize,
  EditorCommand,
  EditorSelection,
  EditorTool,
  EditorViewport,
  LayerVisibility,
  ScreenPoint,
  SnapSettings,
} from "./types.ts";

const DEFAULT_VIEWPORT: EditorViewport = {
  pixelsPerMm: 0.08,
  originXPx: 80,
  originYPx: 680,
};

const DEFAULT_LAYERS: LayerVisibility = {
  grid: true,
  rulers: true,
  rooms: true,
  walls: true,
  openings: true,
  dimensions: true,
  annotations: true,
};

interface EditorStore {
  document: PlanDocument | null;
  activeFloorId: string | null;
  viewport: EditorViewport;
  tool: EditorTool;
  selection: EditorSelection | null;
  layers: LayerVisibility;
  snap: SnapSettings;
  history: CommandHistory;
  loadDocument: (document: PlanDocument) => void;
  setActiveFloor: (floorId: string) => void;
  setTool: (tool: EditorTool) => void;
  select: (selection: EditorSelection | null) => void;
  panBy: (deltaXPx: number, deltaYPx: number) => void;
  zoomAt: (anchor: ScreenPoint, factor: number) => void;
  fitToDocument: (canvas: CanvasSize) => void;
  setLayer: (layer: keyof LayerVisibility, visible: boolean) => void;
  setSnap: (settings: Partial<SnapSettings>) => void;
  stage: (command: EditorCommand) => void;
  undo: () => void;
  redo: () => void;
  clearStaged: () => void;
}

export const useEditorStore = create<EditorStore>((set, get) => ({
  document: null,
  activeFloorId: null,
  viewport: DEFAULT_VIEWPORT,
  tool: "select",
  selection: null,
  layers: DEFAULT_LAYERS,
  snap: { enabled: true, gridMm: 100 },
  history: EMPTY_HISTORY,
  loadDocument: (document) => {
    const firstFloor = document.floors[0];
    if (firstFloor === undefined) {
      throw new RangeError(
        "PlanDocument must contain at least one floor for editing.",
      );
    }
    set({
      document,
      activeFloorId: firstFloor.id,
      selection: null,
      history: EMPTY_HISTORY,
    });
  },
  setActiveFloor: (floorId) => {
    const document = get().document;
    if (
      document === null ||
      !document.floors.some((floor) => floor.id === floorId)
    ) {
      throw new RangeError(
        "Cannot activate a floor that is not in the loaded PlanDocument.",
      );
    }
    set({ activeFloorId: floorId, selection: null });
  },
  setTool: (tool) => {
    set({ tool });
  },
  select: (selection) => {
    set({ selection });
  },
  panBy: (deltaXPx, deltaYPx) => {
    set((state) => ({
      viewport: panViewport(state.viewport, deltaXPx, deltaYPx),
    }));
  },
  zoomAt: (anchor, factor) => {
    set((state) => ({
      viewport: zoomAtScreenPoint(state.viewport, anchor, factor),
    }));
  },
  fitToDocument: (canvas) => {
    const state = get();
    if (state.document === null) {
      return;
    }
    const floor = activeFloor(state.document, state.activeFloorId);
    const polygon = floor.boundary ?? state.document.buildable_area.polygon;
    set({ viewport: fitBoundsToCanvas(polygonBounds(polygon), canvas) });
  },
  setLayer: (layer, visible) => {
    set((state) => ({ layers: { ...state.layers, [layer]: visible } }));
  },
  setSnap: (settings) => {
    set((state) => ({ snap: { ...state.snap, ...settings } }));
  },
  stage: (command) => {
    set((state) => ({
      history: stageCommand(state.history, validateEditorCommand(command)),
    }));
  },
  undo: () => {
    set((state) => ({ history: undoCommand(state.history) }));
  },
  redo: () => {
    set((state) => ({ history: redoCommand(state.history) }));
  },
  clearStaged: () => {
    set({ history: EMPTY_HISTORY });
  },
}));
