from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from maccli import reminders


class RemindersSafetyTests(unittest.TestCase):
    def run_main(self, args: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return reminders.main(args)

    def test_write_commands_require_confirmation_before_osascript(self) -> None:
        cases = [
            ["create", "--list", "Inbox", "--title", "Draft plan"],
            ["update", "--reminder-id", "REMINDER_ID", "--title", "Updated title"],
            ["complete", "--reminder-id", "REMINDER_ID"],
            ["uncomplete", "--reminder-id", "REMINDER_ID"],
            ["move", "--reminder-id", "REMINDER_ID", "--to-list", "Work"],
            ["delete", "--reminder-id", "REMINDER_ID"],
        ]

        with patch("maccli.reminders.run_osascript") as run_osascript:
            for args in cases:
                with self.subTest(args=args):
                    self.assertEqual(self.run_main(args), 2)
                    run_osascript.assert_not_called()

    def test_update_rejects_empty_change(self) -> None:
        with patch("maccli.reminders.run_osascript") as run_osascript:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["update", "--reminder-id", "REMINDER_ID", "--confirm"])
            self.assertEqual(raised.exception.code, 2)
            run_osascript.assert_not_called()

    def test_update_rejects_conflicting_flag_options(self) -> None:
        with patch("maccli.reminders.run_osascript") as run_osascript:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(
                    [
                        "update",
                        "--reminder-id",
                        "REMINDER_ID",
                        "--flagged",
                        "--no-flagged",
                        "--confirm",
                    ]
                )
            self.assertEqual(raised.exception.code, 2)
            run_osascript.assert_not_called()

    def test_create_requires_explicit_list(self) -> None:
        with patch("maccli.reminders.run_osascript") as run_osascript:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["create", "--title", "Draft plan", "--confirm"])
            self.assertEqual(raised.exception.code, 2)
            run_osascript.assert_not_called()


if __name__ == "__main__":
    unittest.main()
