export const PRODUCT_NAME = "AI Vastu Architect" as const;
export const CANONICAL_LINEAR_UNIT = "mm" as const;
export { PlanEditor } from "./components/editor/PlanEditor.tsx";
export { buildChangeSet, validateEditorCommand } from "./editor/commands.ts";
export { useEditorStore } from "./editor/store.ts";
export type {
  EditorChangeSet,
  EditorCommand,
  EditorSelection,
} from "./editor/types.ts";
