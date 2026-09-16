import type { IntPoint, IntPolygon } from "@ai-vastu/contracts";

import type {
  CanvasSize,
  EditorViewport,
  ScreenPoint,
  WorldBounds,
} from "./types.ts";

const MIN_PIXELS_PER_MM = 0.005;
const MAX_PIXELS_PER_MM = 5;
const DEFAULT_PIXELS_PER_MM = 0.08;

export function assertSafeIntegerMm(value: number, label: string): void {
  if (!Number.isSafeInteger(value)) {
    throw new RangeError(
      `${label} must be a JavaScript-safe integer millimetre value.`,
    );
  }
}

export function clampZoom(pixelsPerMm: number): number {
  if (!Number.isFinite(pixelsPerMm)) {
    return DEFAULT_PIXELS_PER_MM;
  }
  return Math.min(MAX_PIXELS_PER_MM, Math.max(MIN_PIXELS_PER_MM, pixelsPerMm));
}

export function worldToScreen(
  point: IntPoint,
  viewport: EditorViewport,
): ScreenPoint {
  assertSafeIntegerMm(point.x_mm, "x_mm");
  assertSafeIntegerMm(point.y_mm, "y_mm");
  return {
    xPx: viewport.originXPx + point.x_mm * viewport.pixelsPerMm,
    yPx: viewport.originYPx - point.y_mm * viewport.pixelsPerMm,
  };
}

export function screenToWorld(
  point: ScreenPoint,
  viewport: EditorViewport,
): { readonly xMm: number; readonly yMm: number } {
  return {
    xMm: (point.xPx - viewport.originXPx) / viewport.pixelsPerMm,
    yMm: (viewport.originYPx - point.yPx) / viewport.pixelsPerMm,
  };
}

export function zoomAtScreenPoint(
  viewport: EditorViewport,
  anchor: ScreenPoint,
  zoomFactor: number,
): EditorViewport {
  const world = screenToWorld(anchor, viewport);
  const pixelsPerMm = clampZoom(viewport.pixelsPerMm * zoomFactor);
  return {
    pixelsPerMm,
    originXPx: anchor.xPx - world.xMm * pixelsPerMm,
    originYPx: anchor.yPx + world.yMm * pixelsPerMm,
  };
}

export function panViewport(
  viewport: EditorViewport,
  deltaXPx: number,
  deltaYPx: number,
): EditorViewport {
  return {
    ...viewport,
    originXPx: viewport.originXPx + deltaXPx,
    originYPx: viewport.originYPx + deltaYPx,
  };
}

export function snapMm(valueMm: number, gridMm: number): number {
  if (!Number.isSafeInteger(gridMm) || gridMm <= 0) {
    throw new RangeError("gridMm must be a positive safe integer.");
  }
  const snapped = Math.round(valueMm / gridMm) * gridMm;
  assertSafeIntegerMm(snapped, "snapped millimetres");
  return snapped;
}

export function polygonBounds(polygon: IntPolygon): WorldBounds {
  if (polygon.outer.length < 3) {
    throw new RangeError(
      "A polygon requires at least three outer-ring points.",
    );
  }
  let minXmm = Number.POSITIVE_INFINITY;
  let minYmm = Number.POSITIVE_INFINITY;
  let maxXmm = Number.NEGATIVE_INFINITY;
  let maxYmm = Number.NEGATIVE_INFINITY;
  for (const point of polygon.outer) {
    assertSafeIntegerMm(point.x_mm, "polygon x_mm");
    assertSafeIntegerMm(point.y_mm, "polygon y_mm");
    minXmm = Math.min(minXmm, point.x_mm);
    minYmm = Math.min(minYmm, point.y_mm);
    maxXmm = Math.max(maxXmm, point.x_mm);
    maxYmm = Math.max(maxYmm, point.y_mm);
  }
  return { minXmm, minYmm, maxXmm, maxYmm };
}

export function fitBoundsToCanvas(
  bounds: WorldBounds,
  canvas: CanvasSize,
  paddingPx = 64,
): EditorViewport {
  const widthMm = Math.max(1, bounds.maxXmm - bounds.minXmm);
  const heightMm = Math.max(1, bounds.maxYmm - bounds.minYmm);
  const usableWidth = Math.max(1, canvas.widthPx - paddingPx * 2);
  const usableHeight = Math.max(1, canvas.heightPx - paddingPx * 2);
  const pixelsPerMm = clampZoom(
    Math.min(usableWidth / widthMm, usableHeight / heightMm),
  );
  const drawingWidth = widthMm * pixelsPerMm;
  const drawingHeight = heightMm * pixelsPerMm;
  const left = (canvas.widthPx - drawingWidth) / 2;
  const top = (canvas.heightPx - drawingHeight) / 2;
  return {
    pixelsPerMm,
    originXPx: left - bounds.minXmm * pixelsPerMm,
    originYPx: top + bounds.maxYmm * pixelsPerMm,
  };
}

export function visibleWorldBounds(
  viewport: EditorViewport,
  canvas: CanvasSize,
): WorldBounds {
  const topLeft = screenToWorld({ xPx: 0, yPx: 0 }, viewport);
  const bottomRight = screenToWorld(
    { xPx: canvas.widthPx, yPx: canvas.heightPx },
    viewport,
  );
  return {
    minXmm: Math.min(topLeft.xMm, bottomRight.xMm),
    minYmm: Math.min(topLeft.yMm, bottomRight.yMm),
    maxXmm: Math.max(topLeft.xMm, bottomRight.xMm),
    maxYmm: Math.max(topLeft.yMm, bottomRight.yMm),
  };
}

export function polygonToScreenPoints(
  polygon: IntPolygon,
  viewport: EditorViewport,
): number[] {
  return polygon.outer.flatMap((point) => {
    const screen = worldToScreen(point, viewport);
    return [screen.xPx, screen.yPx];
  });
}

export function segmentLengthMm(start: IntPoint, end: IntPoint): number {
  const dx = end.x_mm - start.x_mm;
  const dy = end.y_mm - start.y_mm;
  return Math.hypot(dx, dy);
}

export function pointAlongSegment(
  start: IntPoint,
  end: IntPoint,
  distanceMm: number,
): { readonly x_mm: number; readonly y_mm: number } {
  const length = segmentLengthMm(start, end);
  if (length <= 0) {
    throw new RangeError("Cannot project onto a zero-length segment.");
  }
  const t = distanceMm / length;
  return {
    x_mm: start.x_mm + (end.x_mm - start.x_mm) * t,
    y_mm: start.y_mm + (end.y_mm - start.y_mm) * t,
  };
}
