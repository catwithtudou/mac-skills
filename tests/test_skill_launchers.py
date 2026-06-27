from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_CASES = [
    ("macos-calendar", "calendar", "read_calendar.py"),
    ("macos-reminders", "reminders", "read_reminders.py"),
    ("macos-notes", "notes", "read_notes.py"),
]


class SkillLauncherTests(unittest.TestCase):
    def write_executable(self, path: Path, body: str) -> None:
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def copy_skill(self, skill_name: str, tmp_dir: str) -> Path:
        skill_copy = Path(tmp_dir) / skill_name
        shutil.copytree(
            ROOT / "skills" / skill_name,
            skill_copy,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        return skill_copy

    def test_launchers_prefer_local_maccli(self) -> None:
        for skill_name, module_name, script_name in LAUNCHER_CASES:
            with self.subTest(skill=skill_name), tempfile.TemporaryDirectory() as tmp_dir:
                skill_copy = self.copy_skill(skill_name, tmp_dir)
                bin_dir = Path(tmp_dir) / "bin"
                bin_dir.mkdir()
                log_path = Path(tmp_dir) / "maccli.args"
                self.write_executable(
                    bin_dir / "maccli",
                    f'#!/bin/sh\nprintf "%s\\n" "$@" > "{log_path}"\n',
                )
                env = {**os.environ, "PATH": str(bin_dir)}
                env.pop("PYTHONPATH", None)

                completed = subprocess.run(
                    [sys.executable, f"scripts/{script_name}", "--sample"],
                    cwd=skill_copy,
                    env=env,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(log_path.read_text(encoding="utf-8").splitlines(), [module_name, "--sample"])

    def test_launchers_fall_back_to_pinned_npx_package(self) -> None:
        for skill_name, module_name, script_name in LAUNCHER_CASES:
            with self.subTest(skill=skill_name), tempfile.TemporaryDirectory() as tmp_dir:
                skill_copy = self.copy_skill(skill_name, tmp_dir)
                bin_dir = Path(tmp_dir) / "bin"
                bin_dir.mkdir()
                log_path = Path(tmp_dir) / "npx.args"
                self.write_executable(
                    bin_dir / "npx",
                    f'#!/bin/sh\nprintf "%s\\n" "$@" > "{log_path}"\n',
                )
                env = {**os.environ, "PATH": str(bin_dir)}
                env.pop("PYTHONPATH", None)

                completed = subprocess.run(
                    [sys.executable, f"scripts/{script_name}", "--sample"],
                    cwd=skill_copy,
                    env=env,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(
                    log_path.read_text(encoding="utf-8").splitlines(),
                    ["-y", "mac-skills@0.3.1", module_name, "--sample"],
                )

    def test_npm_wrapper_invokes_python_module_with_repo_src(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "python.args"
            env_path = Path(tmp_dir) / "python.env"
            fake_python = Path(tmp_dir) / "python3"
            self.write_executable(
                fake_python,
                f'#!/bin/sh\nprintf "%s\\n" "$@" > "{log_path}"\nprintf "%s" "$PYTHONPATH" > "{env_path}"\n',
            )
            env = {**os.environ, "MACCLI_PYTHON": str(fake_python)}
            completed = subprocess.run(
                ["node", "bin/maccli.js", "reminders", "lists"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                log_path.read_text(encoding="utf-8").splitlines(),
                ["-m", "maccli", "reminders", "lists"],
            )
            self.assertIn(str(ROOT / "src"), env_path.read_text(encoding="utf-8").split(os.pathsep))


if __name__ == "__main__":
    unittest.main()
