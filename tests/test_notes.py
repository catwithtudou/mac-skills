from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from maccli import cli, notes


class NotesCliTests(unittest.TestCase):
    def run_main(self, args: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return notes.main(args)

    def test_top_level_cli_routes_notes(self) -> None:
        with patch("maccli.notes.main", return_value=0) as notes_main:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["notes", "doctor"]), 0)
            notes_main.assert_called_once_with(["doctor"])

    def test_write_commands_require_confirmation_before_osascript(self) -> None:
        cases = [
            ["create", "--account", "iCloud", "--folder", "Notes", "--title", "Draft plan"],
            ["delete", "--note-id", "NOTE_ID", "--confirm-delete"],
        ]

        with patch("maccli.notes.run_osascript") as run_osascript:
            for args in cases:
                with self.subTest(args=args):
                    self.assertEqual(self.run_main(args), 2)
                    run_osascript.assert_not_called()

    def test_delete_requires_second_confirmation_before_osascript(self) -> None:
        with patch("maccli.notes.run_osascript") as run_osascript:
            self.assertEqual(self.run_main(["delete", "--note-id", "NOTE_ID", "--confirm"]), 2)
            run_osascript.assert_not_called()

    def test_named_folder_requires_account_selector(self) -> None:
        with patch("maccli.notes.run_osascript") as run_osascript:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["notes", "--folder", "Notes"])
            self.assertEqual(raised.exception.code, 2)
            run_osascript.assert_not_called()

            with self.assertRaises(SystemExit) as raised:
                self.run_main(["create", "--folder", "Notes", "--title", "Draft", "--confirm"])
            self.assertEqual(raised.exception.code, 2)
            run_osascript.assert_not_called()

    def test_folder_id_does_not_require_account_selector(self) -> None:
        with patch("maccli.notes.run_osascript", return_value=[]) as run_osascript:
            self.assertEqual(self.run_main(["notes", "--folder-id", "FOLDER_ID"]), 0)
            run_osascript.assert_called_once()

    def test_confirmed_create_renders_script_and_calls_osascript_once(self) -> None:
        result = {"id": "NOTE_ID", "name": "Draft plan"}
        with patch("maccli.notes.run_osascript", return_value=result) as run_osascript:
            self.assertEqual(
                self.run_main(
                    [
                        "create",
                        "--account",
                        "iCloud",
                        "--folder",
                        "Notes",
                        "--title",
                        "Draft plan",
                        "--body",
                        "Outline release notes",
                        "--confirm",
                    ]
                ),
                0,
            )

        run_osascript.assert_called_once()
        script, timeout = run_osascript.call_args.args
        self.assertEqual(timeout, notes.DEFAULT_WRITE_TIMEOUT)
        self.assertIn('property targetAccountName : "iCloud"', script)
        self.assertIn('property targetFolderName : "Notes"', script)
        self.assertIn('property noteTitle : "Draft plan"', script)
        self.assertIn("property shouldSetBody : true", script)

    def test_note_read_includes_body_by_default(self) -> None:
        with patch("maccli.notes.run_osascript", return_value={"id": "NOTE_ID"}) as run_osascript:
            self.assertEqual(self.run_main(["note", "--note-id", "NOTE_ID"]), 0)
        script, _ = run_osascript.call_args.args
        self.assertIn("property includeBody : true", script)

    def test_search_body_scan_does_not_force_body_output(self) -> None:
        with patch("maccli.notes.run_osascript", return_value=[]) as run_osascript:
            self.assertEqual(self.run_main(["search", "launch", "--search-body"]), 0)
        script, _ = run_osascript.call_args.args
        self.assertIn("property shouldSearchBody : true", script)
        self.assertIn("property includeBody : false", script)


if __name__ == "__main__":
    unittest.main()
