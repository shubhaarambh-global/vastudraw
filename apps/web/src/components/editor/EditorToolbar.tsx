"use client";

import type { LayerVisibility } from "../../editor/types.ts";

interface EditorToolbarProps {
  readonly tool: "select" | "pan";
  readonly layers: LayerVisibility;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
  readonly stagedCount: number;
  readonly onTool: (tool: "select" | "pan") => void;
  readonly onFit: () => void;
  readonly onUndo: () => void;
  readonly onRedo: () => void;
  readonly onClear: () => void;
  readonly onLayer: (layer: keyof LayerVisibility, visible: boolean) => void;
  readonly onSubmit: () => void;
  readonly canSubmit: boolean;
}

export function EditorToolbar(props: EditorToolbarProps) {
  const layerKeys: readonly (keyof LayerVisibility)[] = [
    "grid",
    "rulers",
    "rooms",
    "walls",
    "openings",
    "dimensions",
  ];
  return (
    <div
      className="editor-toolbar"
      role="toolbar"
      aria-label="Plan editor tools"
    >
      <button
        type="button"
        data-active={props.tool === "select"}
        onClick={() => {
          props.onTool("select");
        }}
      >
        Select
      </button>
      <button
        type="button"
        data-active={props.tool === "pan"}
        onClick={() => {
          props.onTool("pan");
        }}
      >
        Pan
      </button>
      <button type="button" onClick={props.onFit}>
        Fit
      </button>
      <span className="toolbar-separator" />
      <button type="button" disabled={!props.canUndo} onClick={props.onUndo}>
        Undo
      </button>
      <button type="button" disabled={!props.canRedo} onClick={props.onRedo}>
        Redo
      </button>
      <button
        type="button"
        disabled={props.stagedCount === 0}
        onClick={props.onClear}
      >
        Clear staged
      </button>
      <span className="toolbar-separator" />
      {layerKeys.map((layer) => (
        <label className="layer-toggle" key={layer}>
          <input
            type="checkbox"
            checked={props.layers[layer]}
            onChange={(event) => {
              props.onLayer(layer, event.target.checked);
            }}
          />
          {layer}
        </label>
      ))}
      <span className="toolbar-spacer" />
      <span className="staged-count">{props.stagedCount} staged</span>
      <button
        type="button"
        className="primary-action"
        disabled={!props.canSubmit}
        onClick={props.onSubmit}
      >
        Submit exact edits
      </button>
    </div>
  );
}
