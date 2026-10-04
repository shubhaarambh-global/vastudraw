import { existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const repositoryRoot = fileURLToPath(new URL("..", import.meta.url));
const pythonRelative =
  process.platform === "win32"
    ? path.join(".venv", "Scripts", "python.exe")
    : path.join(".venv", "bin", "python");
const pythonExecutable = path.join(repositoryRoot, pythonRelative);

if (!existsSync(pythonExecutable)) {
  process.stderr.write("Project virtual-environment Python is unavailable.\n");
  process.exit(1);
}

const childEnvironment = { ...process.env };
let processTempDirectory = null;
if (process.platform === "win32") {
  const processTempRoot = path.join(repositoryRoot, ".local", "python-process-temp");
  mkdirSync(processTempRoot, { recursive: true });
  processTempDirectory = mkdtempSync(path.join(processTempRoot, "run-"));
  childEnvironment.AI_VASTU_PROCESS_TMP_ROOT = processTempDirectory;
  childEnvironment.AI_VASTU_PYTEST_TMP_ROOT = path.join(
    processTempDirectory,
    "pytest-fixtures",
  );
}

let result;
try {
  result = spawnSync(pythonExecutable, process.argv.slice(2), {
    cwd: repositoryRoot,
    env: childEnvironment,
    shell: false,
    stdio: "inherit",
  });
} finally {
  if (processTempDirectory !== null) {
    rmSync(processTempDirectory, { recursive: true, force: true });
  }
}

if (result.error) {
  process.stderr.write("Project Python process could not be started.\n");
  process.exit(1);
}
if (result.signal !== null) {
  process.stderr.write("Project Python process ended by signal.\n");
  process.exit(1);
}
process.exit(result.status ?? 1);
