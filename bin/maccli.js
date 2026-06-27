#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const packageRoot = path.resolve(__dirname, "..");
const srcPath = path.join(packageRoot, "src");
const pythonPath = process.env.PYTHONPATH
  ? `${srcPath}${path.delimiter}${process.env.PYTHONPATH}`
  : srcPath;
const env = { ...process.env, PYTHONPATH: pythonPath };
const args = ["-m", "maccli", ...process.argv.slice(2)];
const candidates = process.env.MACCLI_PYTHON
  ? [process.env.MACCLI_PYTHON]
  : ["python3", "python"];

for (const candidate of candidates) {
  const result = spawnSync(candidate, args, { env, stdio: "inherit" });
  if (result.error) {
    if (result.error.code === "ENOENT") {
      continue;
    }
    console.error(`mac-skills: failed to launch ${candidate}: ${result.error.message}`);
    process.exit(1);
  }
  if (result.signal) {
    console.error(`mac-skills: ${candidate} exited from signal ${result.signal}`);
    process.exit(1);
  }
  process.exit(result.status ?? 0);
}

console.error("mac-skills requires Python 3. Install Python 3 or set MACCLI_PYTHON.");
process.exit(127);
