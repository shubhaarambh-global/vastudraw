import type { EditorCommand } from "./types.ts";

export interface CommandHistory {
  readonly staged: readonly EditorCommand[];
  readonly redo: readonly EditorCommand[];
}

export const EMPTY_HISTORY: CommandHistory = Object.freeze({
  staged: Object.freeze([]),
  redo: Object.freeze([]),
});

export function stageCommand(
  history: CommandHistory,
  command: EditorCommand,
): CommandHistory {
  return {
    staged: [...history.staged, command],
    redo: [],
  };
}

export function undoCommand(history: CommandHistory): CommandHistory {
  const command = history.staged.at(-1);
  if (command === undefined) {
    return history;
  }
  return {
    staged: history.staged.slice(0, -1),
    redo: [...history.redo, command],
  };
}

export function redoCommand(history: CommandHistory): CommandHistory {
  const command = history.redo.at(-1);
  if (command === undefined) {
    return history;
  }
  return {
    staged: [...history.staged, command],
    redo: history.redo.slice(0, -1),
  };
}
