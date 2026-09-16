import assert from "node:assert/strict";
import test from "node:test";

import {
  EMPTY_HISTORY,
  redoCommand,
  stageCommand,
  undoCommand,
} from "./history.ts";

const command = {
  kind: "WALL_MOVE_PARALLEL",
  wall_id: "wall-1",
  delta_mm: 100,
} as const;

void test("staged edit history has deterministic undo/redo semantics", () => {
  const staged = stageCommand(EMPTY_HISTORY, command);
  assert.equal(staged.staged.length, 1);
  const undone = undoCommand(staged);
  assert.equal(undone.staged.length, 0);
  assert.equal(undone.redo.length, 1);
  const redone = redoCommand(undone);
  assert.deepEqual(redone.staged, [command]);
});
