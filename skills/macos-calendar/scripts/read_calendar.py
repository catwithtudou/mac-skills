#!/usr/bin/env python3
"""Compatibility shim for maccli calendar commands."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


PACKAGE_URL = "git+https://github.com/catwithtudou/mac-skills.git"


def repo_src() -> Path:
    return Path(__file__).resolve().parents[3] / "src"


def run_maccli(args: list[str]) -> int:
    src = repo_src()
    if src.exists():
        sys.path.insert(0, str(src))
        from maccli.cli import main

        return main(["calendar", *args])

    if importlib.util.find_spec("maccli") is None:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", PACKAGE_URL],
            text=True,
        )
        if completed.returncode != 0:
            return completed.returncode

    return subprocess.run([sys.executable, "-m", "maccli", "calendar", *args], text=True).returncode


if __name__ == "__main__":
    raise SystemExit(run_maccli(sys.argv[1:]))
