import assert from "node:assert/strict";
import test from "node:test";

import {
  fitBoundsToCanvas,
  screenToWorld,
  snapMm,
  worldToScreen,
  zoomAtScreenPoint,
} from "./math.ts";
import { formatLengthMm, parseLengthToMm } from "../units/length.ts";

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

void test("architectural display units preserve canonical mm inputs", () => {
  assert.equal(formatLengthMm(9_144, "ft-in"), `30'-0"`);
  assert.equal(formatLengthMm(15_240, "m"), "15.240 m");
  assert.equal(parseLengthToMm(`10'-6 1/2"`, "ft-in"), 3_213);
  assert.equal(parseLengthToMm("9.144 m", "m"), 9_144);
  assert.equal(parseLengthToMm("30", "ft-in"), 9_144);
});
