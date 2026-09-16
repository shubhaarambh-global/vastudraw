import assert from "node:assert/strict";
import test from "node:test";

import { validateEditorCommand } from "./commands.ts";

void test("editor commands reject fractional millimetres", () => {
  assert.throws(
    () =>
      validateEditorCommand({
        kind: "WALL_MOVE_PARALLEL",
        wall_id: "wall-1",
        delta_mm: 0.5,
      }),
    /safe integer/,
  );
});

void test("opening edits reject invalid dimensions", () => {
  assert.throws(
    () =>
      validateEditorCommand({
        kind: "OPENING_RESIZE",
        opening_id: "opening-1",
        width_mm: 0,
      }),
    /positive/,
  );
});
