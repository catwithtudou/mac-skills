from __future__ import annotations

import contextlib
import io
import unittest
from argparse import Namespace
from datetime import datetime
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

    def test_filter_items_matches_query_body_and_due_range(self) -> None:
        args = Namespace(
            query="launch",
            include_body=True,
            due_from="2026-06-15",
            due_to="2026-06-15",
            overdue_before=None,
            date_field="due",
            max=None,
        )
        items = [
            {"name": "Review", "list_name": "Work", "body": "Launch checklist", "due_date": "2026-06-15T09:00:00"},
            {"name": "Review", "list_name": "Work", "body": "Launch checklist", "due_date": "2026-06-16T09:00:00"},
            {"name": "Coffee", "list_name": "Personal", "body": "Buy beans", "due_date": "2026-06-15T09:00:00"},
        ]

        self.assertEqual(reminders.filter_items(items, args), [items[0]])

    def test_date_only_end_filter_is_exclusive_next_midnight(self) -> None:
        self.assertEqual(
            reminders.parse_local_datetime("2026-06-16", date_is_end=True),
            datetime(2026, 6, 17),
        )

    def test_confirmed_create_renders_script_and_calls_osascript_once(self) -> None:
        result = {"id": "REMINDER_ID", "name": "Draft plan"}
        with patch("maccli.reminders.run_osascript", return_value=result) as run_osascript:
            self.assertEqual(
                self.run_main(
                    [
                        "create",
                        "--list",
                        "Inbox",
                        "--title",
                        "Draft plan",
                        "--body",
                        "Outline release notes",
                        "--due",
                        "2026-06-15",
                        "--flagged",
                        "--confirm",
                    ]
                ),
                0,
            )

        run_osascript.assert_called_once()
        script, timeout = run_osascript.call_args.args
        self.assertEqual(timeout, reminders.DEFAULT_WRITE_TIMEOUT)
        self.assertIn('property targetListName : "Inbox"', script)
        self.assertIn('property reminderTitle : "Draft plan"', script)
        self.assertIn("set year of dueDateValue to 2026", script)
        self.assertIn("property reminderFlagged : true", script)


if __name__ == "__main__":
    unittest.main()
