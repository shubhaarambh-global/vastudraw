"use client";

import type { PlanDocument } from "@ai-vastu/contracts";
import { useMemo, useState } from "react";

import {
  PLAN_CANVAS_HEIGHT,
  PLAN_CANVAS_WIDTH,
  createPlanRenderModels,
  type FloorRenderModel,
  type ScreenPoint,
  type SymbolGraphic,
} from "./professional-plan-model.ts";

function points(value: readonly ScreenPoint[]): string {
  return value
    .map((point) => `${String(point.x)},${String(point.y)}`)
    .join(" ");
}

function PresentationSymbol({ symbol }: { readonly symbol: SymbolGraphic }) {
  const centerX = symbol.x + symbol.width / 2;
  const centerY = symbol.y + symbol.height / 2;
  if (symbol.kind === "bed") {
    return (
      <g
        className="plan-symbol plan-symbol-bed"
        data-owner-room-id={symbol.roomId}
      >
        <rect
          x={symbol.x}
          y={symbol.y}
          width={symbol.width}
          height={symbol.height}
          rx="3"
        />
        <line
          x1={symbol.x}
          y1={symbol.y + symbol.height * 0.24}
          x2={symbol.x + symbol.width}
          y2={symbol.y + symbol.height * 0.24}
        />
        <line
          x1={centerX}
          y1={symbol.y}
          x2={centerX}
          y2={symbol.y + symbol.height * 0.24}
        />
      </g>
    );
  }
  if (symbol.kind === "sofa") {
    return (
      <g
        className="plan-symbol plan-symbol-sofa"
        data-owner-room-id={symbol.roomId}
      >
        <rect
          x={symbol.x}
          y={symbol.y}
          width={symbol.width}
          height={symbol.height}
          rx="7"
        />
        <rect
          x={symbol.x + 5}
          y={symbol.y + 5}
          width={Math.max(1, symbol.width - 10)}
          height={Math.max(1, symbol.height - 10)}
          rx="5"
        />
      </g>
    );
  }
  if (symbol.kind === "dining") {
    return (
      <g
        className="plan-symbol plan-symbol-dining"
        data-owner-room-id={symbol.roomId}
      >
        <rect
          x={symbol.x}
          y={symbol.y}
          width={symbol.width}
          height={symbol.height}
          rx="5"
        />
        <circle cx={centerX} cy={symbol.y - 5} r="4" />
        <circle cx={centerX} cy={symbol.y + symbol.height + 5} r="4" />
        <circle cx={symbol.x - 5} cy={centerY} r="4" />
        <circle cx={symbol.x + symbol.width + 5} cy={centerY} r="4" />
      </g>
    );
  }
  if (symbol.kind === "sanitary") {
    return (
      <g
        className="plan-symbol plan-symbol-sanitary"
        data-owner-room-id={symbol.roomId}
      >
        <ellipse
          cx={symbol.x + symbol.width * 0.3}
          cy={centerY}
          rx={symbol.width * 0.28}
          ry={symbol.height * 0.45}
        />
        <rect
          x={symbol.x + symbol.width * 0.62}
          y={symbol.y}
          width={symbol.width * 0.36}
          height={symbol.height * 0.42}
          rx="3"
        />
        <ellipse
          cx={symbol.x + symbol.width * 0.8}
          cy={symbol.y + symbol.height * 0.2}
          rx={symbol.width * 0.12}
          ry={symbol.height * 0.1}
        />
      </g>
    );
  }
  if (symbol.kind === "kitchen-counter") {
    return (
      <g
        className="plan-symbol plan-symbol-kitchen"
        data-owner-room-id={symbol.roomId}
      >
        <rect
          x={symbol.x}
          y={symbol.y}
          width={symbol.width}
          height={symbol.height}
        />
        <rect
          x={symbol.x + symbol.width * 0.43}
          y={symbol.y + 3}
          width={symbol.width * 0.25}
          height={Math.max(2, symbol.height - 6)}
          rx="3"
        />
        <circle
          cx={symbol.x + symbol.width * 0.12}
          cy={centerY}
          r={Math.min(5, symbol.height * 0.2)}
        />
      </g>
    );
  }
  if (symbol.kind === "vehicle") {
    return (
      <g
        className="plan-symbol plan-symbol-vehicle"
        data-owner-room-id={symbol.roomId}
      >
        <rect
          x={symbol.x}
          y={symbol.y}
          width={symbol.width}
          height={symbol.height}
          rx="12"
        />
        <path
          d={`M ${String(symbol.x)} ${String(symbol.y + symbol.height * 0.25)} H ${String(symbol.x + symbol.width)} M ${String(symbol.x)} ${String(symbol.y + symbol.height * 0.75)} H ${String(symbol.x + symbol.width)}`}
        />
      </g>
    );
  }
  return (
    <g
      className="plan-symbol plan-symbol-desk"
      data-owner-room-id={symbol.roomId}
    >
      <rect
        x={symbol.x}
        y={symbol.y}
        width={symbol.width}
        height={symbol.height}
        rx="3"
      />
      <circle cx={centerX} cy={symbol.y + symbol.height + 5} r="4" />
    </g>
  );
}

function FloorSheet({ model }: { readonly model: FloorRenderModel }) {
  return (
    <svg
      className="phase26c3-plan-canvas"
      viewBox={`0 0 ${String(PLAN_CANVAS_WIDTH)} ${String(PLAN_CANVAS_HEIGHT)}`}
      role="img"
      aria-label={`${model.floorName} professional architectural plan`}
      data-floor-index={model.floorIndex}
    >
      <defs>
        <marker
          id={`plan-arrow-${model.floorId}`}
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="3"
          orient="auto"
        >
          <path d="M0,0 L0,6 L7,3 z" className="plan-arrow-head" />
        </marker>
      </defs>

      <g data-layer="site-background">
        {model.roads.map((road) => (
          <g
            key={road.id}
            className="plan-road"
            data-primary-access={road.primaryAccess}
          >
            {road.segments.map((segment, index) => (
              <line
                key={index}
                x1={segment.start.x}
                y1={segment.start.y}
                x2={segment.end.x}
                y2={segment.end.y}
                strokeWidth={road.widthPx}
              />
            ))}
          </g>
        ))}
        <polygon
          className="phase26c3-plot-outline"
          points={points(model.plotPoints)}
        />
        {model.siteSpaces.map((space) => (
          <g key={space.id} data-site-kind={space.kind}>
            <polygon
              className={`plan-site-space plan-site-${space.kind.toLowerCase().replaceAll("_", "-")}`}
              points={points(space.points)}
            />
            <text
              className="plan-site-label"
              x={space.labelPoint.x}
              y={space.labelPoint.y}
              textAnchor="middle"
            >
              {space.label}
            </text>
          </g>
        ))}
        <polygon
          className="plan-buildable-outline"
          points={points(model.buildablePoints)}
        />
        <polygon
          className="plan-floor-outline"
          points={points(model.floorPoints)}
        />
      </g>

      <g data-layer="room-fills">
        {model.rooms.map((room) => (
          <polygon
            key={room.id}
            className={`plan-room-fill plan-room-${room.roomType}`}
            points={points(room.points)}
          />
        ))}
      </g>

      <g data-layer="presentation-furniture">
        {model.canonicalFurniture.map((item) => (
          <polygon
            key={item.id}
            className="plan-canonical-object"
            data-object-kind={item.kind}
            points={points(item.points)}
          />
        ))}
        {model.canonicalFixtures.map((item) => (
          <g
            key={item.id}
            className="plan-canonical-object"
            data-object-kind={item.kind}
          >
            {item.points.length > 0 ? (
              <polygon points={points(item.points)} />
            ) : null}
            {item.anchor ? (
              <circle cx={item.anchor.x} cy={item.anchor.y} r="4" />
            ) : null}
          </g>
        ))}
        {model.symbols.map((symbol) => (
          <PresentationSymbol
            key={`${symbol.roomId}:${symbol.kind}`}
            symbol={symbol}
          />
        ))}
      </g>

      <g data-layer="stairs">
        {model.stairs.map((stair) => (
          <g key={stair.id} className="plan-stair" data-stair-id={stair.id}>
            <polygon points={points(stair.points)} />
            {stair.treads.map((tread, index) => (
              <line
                key={index}
                className="plan-stair-tread"
                x1={tread.start.x}
                y1={tread.start.y}
                x2={tread.end.x}
                y2={tread.end.y}
              />
            ))}
            <line
              className="plan-stair-landing"
              x1={stair.landing.start.x}
              y1={stair.landing.start.y}
              x2={stair.landing.end.x}
              y2={stair.landing.end.y}
            />
            <line
              className="plan-stair-divider"
              x1={stair.divider.start.x}
              y1={stair.divider.start.y}
              x2={stair.divider.end.x}
              y2={stair.divider.end.y}
            />
            <line
              className="plan-stair-arrow"
              x1={stair.arrow.start.x}
              y1={stair.arrow.start.y}
              x2={stair.arrow.end.x}
              y2={stair.arrow.end.y}
              markerEnd={`url(#plan-arrow-${model.floorId})`}
            />
            <text
              className="plan-stair-up"
              x={stair.arrow.end.x}
              y={stair.arrow.end.y - 8}
              textAnchor="middle"
            >
              UP
            </text>
          </g>
        ))}
      </g>

      <g data-layer="walls">
        {model.walls.map((wall) => (
          <line
            key={wall.id}
            className={`plan-wall plan-wall-${wall.category.toLowerCase()}`}
            x1={wall.start.x}
            y1={wall.start.y}
            x2={wall.end.x}
            y2={wall.end.y}
            strokeWidth={wall.thicknessPx}
          />
        ))}
      </g>

      <g data-layer="openings">
        {model.windows.map((window) => (
          <g
            key={window.id}
            className="plan-window"
            data-opening-id={window.id}
          >
            {window.lines.map((line, index) => (
              <line
                key={index}
                x1={line.start.x}
                y1={line.start.y}
                x2={line.end.x}
                y2={line.end.y}
              />
            ))}
          </g>
        ))}
        {model.doors.map((door) => (
          <g
            key={door.id}
            className="plan-door"
            data-opening-id={door.id}
            data-derived-swing={door.derivedSwing}
          >
            <line
              className="plan-door-leaf"
              x1={door.leaf.start.x}
              y1={door.leaf.start.y}
              x2={door.leaf.end.x}
              y2={door.leaf.end.y}
            />
            {door.arcPoints.length > 0 ? (
              <polyline
                className="plan-door-swing"
                points={points(door.arcPoints)}
              />
            ) : null}
          </g>
        ))}
      </g>

      <g data-layer="room-labels">
        {model.rooms.map((room) => (
          <text
            key={room.id}
            className="phase26c3-room-label"
            x={room.labelPoint.x}
            y={room.labelPoint.y}
            textAnchor="middle"
          >
            <tspan className="plan-room-name" x={room.labelPoint.x} dy="-0.1em">
              {room.title}
            </tspan>
            <tspan
              className="plan-room-dimension"
              x={room.labelPoint.x}
              dy="1.35em"
            >
              {room.dimension}
            </tspan>
          </text>
        ))}
      </g>

      <g data-layer="dimensions">
        {model.dimensions.map((dimension, index) => {
          const midpoint = {
            x: (dimension.start.x + dimension.end.x) / 2,
            y: (dimension.start.y + dimension.end.y) / 2,
          };
          return (
            <g
              key={`${dimension.category}:${String(index)}`}
              className="plan-dimension"
              data-dimension-category={dimension.category}
            >
              <line
                className="plan-extension-line"
                x1={dimension.sourceStart.x}
                y1={dimension.sourceStart.y}
                x2={dimension.start.x}
                y2={dimension.start.y}
              />
              <line
                className="plan-extension-line"
                x1={dimension.sourceEnd.x}
                y1={dimension.sourceEnd.y}
                x2={dimension.end.x}
                y2={dimension.end.y}
              />
              <line
                className="plan-dimension-line"
                x1={dimension.start.x}
                y1={dimension.start.y}
                x2={dimension.end.x}
                y2={dimension.end.y}
              />
              <line
                className="plan-dimension-tick"
                x1={dimension.start.x - 4}
                y1={dimension.start.y + 4}
                x2={dimension.start.x + 4}
                y2={dimension.start.y - 4}
              />
              <line
                className="plan-dimension-tick"
                x1={dimension.end.x - 4}
                y1={dimension.end.y + 4}
                x2={dimension.end.x + 4}
                y2={dimension.end.y - 4}
              />
              <text x={midpoint.x} y={midpoint.y - 5} textAnchor="middle">
                {dimension.label}
              </text>
            </g>
          );
        })}
      </g>

      <g data-layer="sheet-annotations">
        <text className="plan-sheet-brand" x="34" y="35">
          VASTUDRAW
        </text>
        <text className="plan-sheet-floor" x="34" y="53">
          {model.floorName.toUpperCase()}
        </text>
        <line
          className="phase26c3-north-line"
          x1={model.north.start.x}
          y1={model.north.start.y}
          x2={model.north.end.x}
          y2={model.north.end.y}
          markerEnd={`url(#plan-arrow-${model.floorId})`}
        />
        <text
          className="phase26c3-north"
          x={model.northLabel.x}
          y={model.northLabel.y}
          textAnchor="middle"
        >
          N
        </text>
        <line
          className="plan-scale-bar"
          x1={model.scaleBar.start.x}
          y1={model.scaleBar.start.y}
          x2={model.scaleBar.end.x}
          y2={model.scaleBar.end.y}
        />
        <line
          className="plan-scale-tick"
          x1={model.scaleBar.start.x}
          y1={model.scaleBar.start.y - 5}
          x2={model.scaleBar.start.x}
          y2={model.scaleBar.start.y + 5}
        />
        <line
          className="plan-scale-tick"
          x1={model.scaleBar.end.x}
          y1={model.scaleBar.end.y - 5}
          x2={model.scaleBar.end.x}
          y2={model.scaleBar.end.y + 5}
        />
        <text
          className="plan-scale-label"
          x={(model.scaleBar.start.x + model.scaleBar.end.x) / 2}
          y={model.scaleBar.start.y - 8}
          textAnchor="middle"
        >
          {model.scaleLabel}
        </text>
        <text
          className="plan-units-label"
          x={PLAN_CANVAS_WIDTH - 34}
          y={PLAN_CANVAS_HEIGHT - 25}
          textAnchor="end"
        >
          CANONICAL GEOMETRY · mm
        </text>
      </g>
    </svg>
  );
}

export function ProfessionalPlanCanvas({
  document,
}: {
  readonly document: PlanDocument | null;
}) {
  const models = useMemo(
    () => (document ? createPlanRenderModels(document) : []),
    [document],
  );
  const [activeFloorId, setActiveFloorId] = useState<string | null>(null);
  const firstModel = models[0];
  if (!document || firstModel === undefined) {
    return (
      <div className="phase26c3-plan-empty">
        Canonical candidate geometry is unavailable.
      </div>
    );
  }
  const active =
    models.find((model) => model.floorId === activeFloorId) ?? firstModel;
  return (
    <div className="professional-plan-viewer">
      {models.length > 1 ? (
        <div
          className="professional-floor-tabs"
          role="tablist"
          aria-label="Building floors"
        >
          {models.map((model) => (
            <button
              key={model.floorId}
              type="button"
              role="tab"
              aria-selected={model.floorId === active.floorId}
              data-active={model.floorId === active.floorId}
              onClick={() => {
                setActiveFloorId(model.floorId);
              }}
            >
              {model.floorName}
            </button>
          ))}
        </div>
      ) : null}
      <FloorSheet model={active} />
      <span
        className="professional-floor-count"
        aria-label={`${String(models.length)} canonical floors`}
      >
        {String(active.floorIndex + 1)} / {String(models.length)}
      </span>
    </div>
  );
}
