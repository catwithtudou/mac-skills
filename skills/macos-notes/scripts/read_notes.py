#!/usr/bin/env python3
"""Launch maccli notes from a local install or pinned npm fallback."""

from __future__ import annotations

import shutil
import subprocess
import sys


APP_NAME = "notes"
NPX_PACKAGE = "mac-skills@0.3.1"


def run_maccli(args: list[str]) -> int:
    maccli = shutil.which("maccli")
    if maccli:
        return subprocess.run([maccli, APP_NAME, *args], text=True).returncode

    npx = shutil.which("npx")
    if npx:
        return subprocess.run([npx, "-y", NPX_PACKAGE, APP_NAME, *args], text=True).returncode

    print(
        "maccli was not found and npx is unavailable. Install with: npm install -g mac-skills",
        file=sys.stderr,
    )
    return 127


if __name__ == "__main__":
    raise SystemExit(run_maccli(sys.argv[1:]))
