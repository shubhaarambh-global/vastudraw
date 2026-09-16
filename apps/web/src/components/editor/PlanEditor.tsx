"use client";

import type { PlanDocument, Wall } from "@ai-vastu/contracts";
import Konva from "konva";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Circle, Layer, Line, Rect, Stage, Text } from "react-konva";

import { buildChangeSet } from "../../editor/commands.ts";
import {
  activeFloor,
  indexFloor,
  openingEndpoints,
  openingPreview,
  roomLocked,
  wallPreview,
} from "../../editor/document.ts";
import {
  polygonToScreenPoints,
  segmentLengthMm,
  visibleWorldBounds,
  worldToScreen,
} from "../../editor/math.ts";
import { useEditorStore } from "../../editor/store.ts";
import type {
  CanvasSize,
  EditorChangeSet,
  EditorCommand,
  LayerVisibility,
} from "../../editor/types.ts";
import { EditorToolbar } from "./EditorToolbar.tsx";
import { InspectorPanel } from "./InspectorPanel.tsx";

interface PlanEditorProps {
  readonly document: PlanDocument;
  readonly onSubmitChangeSet?: (changeSet: EditorChangeSet) => void;
}

const RULER_PX = 28;

function GridLayer(props: { readonly size: CanvasSize }) {
  const viewport = useEditorStore((state) => state.viewport);
  const snap = useEditorStore((state) => state.snap);
  const bounds = visibleWorldBounds(viewport, props.size);
  const gridMm = snap.gridMm;
  const firstX = Math.floor(bounds.minXmm / gridMm) * gridMm;
  const firstY = Math.floor(bounds.minYmm / gridMm) * gridMm;
  const lines: React.ReactNode[] = [];
  let count = 0;
  for (
    let x = firstX;
    x <= bounds.maxXmm && count < 500;
    x += gridMm, count += 1
  ) {
    // Viewport bounds are display-derived floats; canonical transforms receive only integer-mm coordinates.
    const screen = worldToScreen({ x_mm: x, y_mm: 0 }, viewport);
    lines.push(
      <Line
        key={`gx-${String(x)}`}
        points={[screen.xPx, 0, screen.xPx, props.size.heightPx]}
        stroke={x % 1000 === 0 ? "#d3d8df" : "#eceff3"}
        strokeWidth={1}
        listening={false}
      />,
    );
  }
  count = 0;
  for (
    let y = firstY;
    y <= bounds.maxYmm && count < 500;
    y += gridMm, count += 1
  ) {
    // Viewport bounds stay display-only; canonical transforms receive only integer-mm coordinates.
    const screen = worldToScreen({ x_mm: 0, y_mm: y }, viewport);
    lines.push(
      <Line
        key={`gy-${String(y)}`}
        points={[0, screen.yPx, props.size.widthPx, screen.yPx]}
        stroke={y % 1000 === 0 ? "#d3d8df" : "#eceff3"}
        strokeWidth={1}
        listening={false}
      />,
    );
  }
  return <Layer listening={false}>{lines}</Layer>;
}

function RulerLayer(props: { readonly size: CanvasSize }) {
  const viewport = useEditorStore((state) => state.viewport);
  const bounds = visibleWorldBounds(viewport, props.size);
  const tickMm =
    viewport.pixelsPerMm >= 0.25
      ? 500
      : viewport.pixelsPerMm >= 0.08
        ? 1000
        : 2000;
  const nodes: React.ReactNode[] = [
    <Rect
      key="top-bg"
      x={0}
      y={0}
      width={props.size.widthPx}
      height={RULER_PX}
      fill="#f8fafc"
      listening={false}
    />,
    <Rect
      key="left-bg"
      x={0}
      y={0}
      width={RULER_PX}
      height={props.size.heightPx}
      fill="#f8fafc"
      listening={false}
    />,
  ];
  const firstX = Math.floor(bounds.minXmm / tickMm) * tickMm;
  for (
    let x = firstX, count = 0;
    x <= bounds.maxXmm && count < 100;
    x += tickMm, count += 1
  ) {
    const screen = worldToScreen({ x_mm: x, y_mm: 0 }, viewport);
    nodes.push(
      <Line
        key={`rx-${String(x)}`}
        points={[screen.xPx, 18, screen.xPx, RULER_PX]}
        stroke="#667085"
        strokeWidth={1}
        listening={false}
      />,
    );
    nodes.push(
      <Text
        key={`rxt-${String(x)}`}
        x={screen.xPx + 3}
        y={4}
        text={String(x)}
        fontSize={9}
        fill="#475467"
        listening={false}
      />,
    );
  }
  const firstY = Math.floor(bounds.minYmm / tickMm) * tickMm;
  for (
    let y = firstY, count = 0;
    y <= bounds.maxYmm && count < 100;
    y += tickMm, count += 1
  ) {
    const screen = worldToScreen({ x_mm: 0, y_mm: y }, viewport);
    nodes.push(
      <Line
        key={`ry-${String(y)}`}
        points={[18, screen.yPx, RULER_PX, screen.yPx]}
        stroke="#667085"
        strokeWidth={1}
        listening={false}
      />,
    );
    nodes.push(
      <Text
        key={`ryt-${String(y)}`}
        x={2}
        y={screen.yPx - 10}
        text={String(y)}
        fontSize={8}
        fill="#475467"
        rotation={-90}
        listening={false}
      />,
    );
  }
  return <Layer listening={false}>{nodes}</Layer>;
}

function canonicalWallColor(wall: Wall): string {
  return wall.category === "EXTERNAL" ? "#182230" : "#344054";
}

export function PlanEditor({ document, onSubmitChangeSet }: PlanEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const [canvasSize, setCanvasSize] = useState<CanvasSize>({
    widthPx: 1_000,
    heightPx: 680,
  });

  const stateDocument = useEditorStore((state) => state.document);
  const activeFloorId = useEditorStore((state) => state.activeFloorId);
  const viewport = useEditorStore((state) => state.viewport);
  const tool = useEditorStore((state) => state.tool);
  const selection = useEditorStore((state) => state.selection);
  const layers = useEditorStore((state) => state.layers);
  const snap = useEditorStore((state) => state.snap);
  const history = useEditorStore((state) => state.history);
  const loadDocument = useEditorStore((state) => state.loadDocument);
  const setTool = useEditorStore((state) => state.setTool);
  const select = useEditorStore((state) => state.select);
  const panBy = useEditorStore((state) => state.panBy);
  const zoomAt = useEditorStore((state) => state.zoomAt);
  const fitToDocument = useEditorStore((state) => state.fitToDocument);
  const setLayer = useEditorStore((state) => state.setLayer);
  const stage = useEditorStore((state) => state.stage);
  const undo = useEditorStore((state) => state.undo);
  const redo = useEditorStore((state) => state.redo);
  const clearStaged = useEditorStore((state) => state.clearStaged);

  useEffect(() => {
    loadDocument(document);
  }, [document, loadDocument]);

  useEffect(() => {
    const element = containerRef.current;
    if (element === null) return;
    const observer = new ResizeObserver(([entry]) => {
      if (entry === undefined) return;
      const widthPx = Math.max(320, Math.floor(entry.contentRect.width));
      const heightPx = Math.max(520, Math.floor(entry.contentRect.height));
      setCanvasSize({ widthPx, heightPx });
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    if (stateDocument !== null) fitToDocument(canvasSize);
  }, [
    stateDocument,
    activeFloorId,
    canvasSize.widthPx,
    canvasSize.heightPx,
    fitToDocument,
  ]);

  const floor = useMemo(() => {
    if (stateDocument === null) return null;
    return activeFloor(stateDocument, activeFloorId);
  }, [stateDocument, activeFloorId]);
  const index = useMemo(
    () => (floor === null ? null : indexFloor(floor)),
    [floor],
  );

  if (stateDocument === null || floor === null || index === null) {
    return (
      <div className="editor-loading">Loading canonical PlanDocument…</div>
    );
  }

  const handleLayer = (layer: keyof LayerVisibility, visible: boolean) => {
    setLayer(layer, visible);
  };
  const submit = () => {
    if (onSubmitChangeSet !== undefined && history.staged.length > 0) {
      onSubmitChangeSet(buildChangeSet(stateDocument, history.staged));
    }
  };

  return (
    <div className="editor-shell">
      <EditorToolbar
        tool={tool}
        layers={layers}
        canUndo={history.staged.length > 0}
        canRedo={history.redo.length > 0}
        stagedCount={history.staged.length}
        onTool={setTool}
        onFit={() => {
          fitToDocument(canvasSize);
        }}
        onUndo={undo}
        onRedo={redo}
        onClear={clearStaged}
        onLayer={handleLayer}
        onSubmit={submit}
        canSubmit={onSubmitChangeSet !== undefined && history.staged.length > 0}
      />
      <div className="editor-main">
        <div className="canvas-wrap" ref={containerRef}>
          <Stage
            ref={stageRef}
            width={canvasSize.widthPx}
            height={canvasSize.heightPx}
            draggable={tool === "pan"}
            onDragEnd={(event) => {
              panBy(event.target.x(), event.target.y());
              event.target.position({ x: 0, y: 0 });
            }}
            onWheel={(event) => {
              event.evt.preventDefault();
              const stageNode = stageRef.current;
              const pointer = stageNode?.getPointerPosition();
              if (pointer === null || pointer === undefined) return;
              zoomAt(
                { xPx: pointer.x, yPx: pointer.y },
                event.evt.deltaY < 0 ? 1.12 : 1 / 1.12,
              );
            }}
            onPointerDown={(event) => {
              if (event.target === event.target.getStage()) select(null);
            }}
          >
            {layers.grid ? <GridLayer size={canvasSize} /> : null}
            <Layer>
              {layers.rooms
                ? (floor.rooms ?? []).map((room) => {
                    const selected =
                      selection?.kind === "room" && selection.id === room.id;
                    const locked = roomLocked(
                      room.locked ?? false,
                      room.id,
                      history.staged,
                    );
                    const points = polygonToScreenPoints(
                      room.polygon,
                      viewport,
                    );
                    const centerX =
                      room.polygon.outer.reduce(
                        (sum, point) => sum + point.x_mm,
                        0,
                      ) / room.polygon.outer.length;
                    const centerY =
                      room.polygon.outer.reduce(
                        (sum, point) => sum + point.y_mm,
                        0,
                      ) / room.polygon.outer.length;
                    const center = worldToScreen(
                      { x_mm: centerX, y_mm: centerY },
                      viewport,
                    );
                    return (
                      <React.Fragment key={room.id}>
                        <Line
                          points={points}
                          closed
                          fill={
                            selected
                              ? "rgba(46, 144, 250, 0.18)"
                              : "rgba(255,255,255,0.92)"
                          }
                          stroke={selected ? "#1570ef" : "#98a2b3"}
                          strokeWidth={selected ? 2 : 1}
                          onClick={(event) => {
                            event.cancelBubble = true;
                            select({ kind: "room", id: room.id });
                          }}
                        />
                        <Text
                          x={center.xPx - 60}
                          y={center.yPx - 8}
                          width={120}
                          align="center"
                          text={`${locked ? "\u{1F512} " : ""}${room.name ?? room.room_type}`}
                          fontSize={12}
                          fill="#344054"
                          listening={false}
                        />
                      </React.Fragment>
                    );
                  })
                : null}
              {layers.walls
                ? (floor.walls ?? []).map((wall) => {
                    const preview = wallPreview(wall, history.staged);
                    const start = worldToScreen(preview.start, viewport);
                    const end = worldToScreen(preview.end, viewport);
                    const selected =
                      selection?.kind === "wall" && selection.id === wall.id;
                    return (
                      <Line
                        key={wall.id}
                        points={[start.xPx, start.yPx, end.xPx, end.yPx]}
                        stroke={
                          preview.pending
                            ? "#f79009"
                            : selected
                              ? "#1570ef"
                              : canonicalWallColor(wall)
                        }
                        strokeWidth={Math.max(
                          2,
                          wall.thickness_mm * viewport.pixelsPerMm,
                        )}
                        {...(preview.pending ? { dash: [8, 5] } : {})}
                        lineCap="square"
                        onClick={(event) => {
                          event.cancelBubble = true;
                          select({ kind: "wall", id: wall.id });
                        }}
                      />
                    );
                  })
                : null}
              {layers.openings
                ? (floor.openings ?? []).map((opening) => {
                    const canonicalWall = index.wallsById.get(opening.wall_id);
                    if (canonicalWall === undefined) return null;
                    const wall = wallPreview(canonicalWall, history.staged);
                    const preview = openingPreview(opening, history.staged);
                    const endpoints = openingEndpoints(wall, preview);
                    const start = worldToScreen(endpoints.start, viewport);
                    const end = worldToScreen(endpoints.end, viewport);
                    const selected =
                      selection?.kind === "opening" &&
                      selection.id === opening.id;
                    return (
                      <Line
                        key={opening.id}
                        points={[start.xPx, start.yPx, end.xPx, end.yPx]}
                        stroke={
                          preview.pending
                            ? "#f79009"
                            : selected
                              ? "#1570ef"
                              : "#12b76a"
                        }
                        strokeWidth={Math.max(
                          5,
                          canonicalWall.thickness_mm * viewport.pixelsPerMm + 3,
                        )}
                        onClick={(event) => {
                          event.cancelBubble = true;
                          select({ kind: "opening", id: opening.id });
                        }}
                      />
                    );
                  })
                : null}
              {layers.dimensions
                ? (floor.dimensions ?? []).map((dimension) => {
                    const start = worldToScreen(dimension.start, viewport);
                    const end = worldToScreen(dimension.end, viewport);
                    const length = segmentLengthMm(
                      dimension.start,
                      dimension.end,
                    );
                    const horizontal =
                      dimension.start.y_mm === dimension.end.y_mm;
                    const offsetPx =
                      (dimension.offset_mm ?? 0) * viewport.pixelsPerMm;
                    const dx = horizontal ? 0 : -offsetPx;
                    const dy = horizontal ? offsetPx : 0;
                    return (
                      <React.Fragment key={dimension.id}>
                        <Line
                          points={[
                            start.xPx + dx,
                            start.yPx + dy,
                            end.xPx + dx,
                            end.yPx + dy,
                          ]}
                          stroke="#667085"
                          strokeWidth={1}
                          dash={[3, 3]}
                          onClick={(event) => {
                            event.cancelBubble = true;
                            select({ kind: "dimension", id: dimension.id });
                          }}
                        />
                        <Text
                          x={(start.xPx + end.xPx) / 2 + dx - 35}
                          y={(start.yPx + end.yPx) / 2 + dy - 14}
                          width={70}
                          align="center"
                          text={
                            dimension.label_override ??
                            `${String(Math.round(length))} mm`
                          }
                          fontSize={10}
                          fill="#475467"
                          listening={false}
                        />
                      </React.Fragment>
                    );
                  })
                : null}
              {selection !== null ? (
                <Circle
                  x={RULER_PX / 2}
                  y={RULER_PX / 2}
                  radius={4}
                  fill="#1570ef"
                  listening={false}
                />
              ) : null}
            </Layer>
            {layers.rulers ? <RulerLayer size={canvasSize} /> : null}
          </Stage>
          <div className="viewport-readout">
            {Math.round(viewport.pixelsPerMm * 1000) / 1000} px/mm · grid{" "}
            {snap.gridMm} mm
          </div>
        </div>
        <InspectorPanel
          key={`${selection?.kind ?? "none"}:${selection?.id ?? "none"}`}
          index={index}
          selection={selection}
          commands={history.staged}
          onStage={(command: EditorCommand) => {
            stage(command);
          }}
        />
      </div>
    </div>
  );
}
