import assert from "node:assert/strict";
import test from "node:test";

import {
  fitBoundsToCanvas,
  screenToWorld,
  snapMm,
  worldToScreen,
  zoomAtScreenPoint,
} from "./math.ts";

void test("world/screen transform preserves +Y-up canonical coordinates", () => {
  const viewport = { pixelsPerMm: 0.1, originXPx: 100, originYPx: 500 };
  const point = { x_mm: 2_000, y_mm: 3_000 };
  const screen = worldToScreen(point, viewport);
  assert.deepEqual(screen, { xPx: 300, yPx: 200 });
  const world = screenToWorld(screen, viewport);
  assert.equal(world.xMm, point.x_mm);
  assert.equal(world.yMm, point.y_mm);
});

void test("zoom is anchored under the cursor", () => {
  const viewport = { pixelsPerMm: 0.1, originXPx: 100, originYPx: 500 };
  const anchor = { xPx: 320, yPx: 240 };
  const before = screenToWorld(anchor, viewport);
  const afterViewport = zoomAtScreenPoint(viewport, anchor, 1.5);
  const after = screenToWorld(anchor, afterViewport);
  assert.ok(Math.abs(after.xMm - before.xMm) < 1e-9);
  assert.ok(Math.abs(after.yMm - before.yMm) < 1e-9);
});

void test("fit and snap stay deterministic", () => {
  const viewport = fitBoundsToCanvas(
    { minXmm: 0, minYmm: 0, maxXmm: 12_000, maxYmm: 9_000 },
    { widthPx: 1_200, heightPx: 800 },
  );
  assert.equal(viewport.pixelsPerMm, 0.07466666666666667);
  assert.equal(snapMm(1_249, 100), 1_200);
  assert.equal(snapMm(1_251, 100), 1_300);
});
