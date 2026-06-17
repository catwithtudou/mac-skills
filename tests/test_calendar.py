from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from maccli import calendar


class CalendarCliTests(unittest.TestCase):
    def run_main(self, args: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return calendar.main(args)

    def test_write_commands_require_confirmation_before_accli(self) -> None:
        cases = [
            [
                "create",
                "--calendar",
                "Work",
                "--summary",
                "Project review",
                "--start",
                "2026-06-15T14:00",
                "--end",
                "2026-06-15T15:00",
            ],
            ["update", "--calendar", "Work", "--event-id", "EVENT_ID", "--summary", "Updated title"],
            ["delete", "--calendar", "Work", "--event-id", "EVENT_ID"],
        ]

        with patch("maccli.calendar.run_accli") as run_accli:
            for args in cases:
                with self.subTest(args=args):
                    self.assertEqual(self.run_main(args), 2)
                    run_accli.assert_not_called()

    def test_update_rejects_empty_change(self) -> None:
        with patch("maccli.calendar.run_accli") as run_accli:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["update", "--calendar", "Work", "--event-id", "EVENT_ID", "--confirm"])
            self.assertEqual(raised.exception.code, 2)
            run_accli.assert_not_called()

    def test_update_rejects_conflicting_all_day_options(self) -> None:
        with patch("maccli.calendar.run_accli") as run_accli:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(
                    [
                        "update",
                        "--calendar",
                        "Work",
                        "--event-id",
                        "EVENT_ID",
                        "--all-day",
                        "--no-all-day",
                        "--confirm",
                    ]
                )
            self.assertEqual(raised.exception.code, 2)
            run_accli.assert_not_called()

    def test_freebusy_requires_calendar_selector(self) -> None:
        with patch("maccli.calendar.run_accli") as run_accli:
            with self.assertRaises(SystemExit) as raised:
                self.run_main(["freebusy", "--from", "2026-06-15T09:00", "--to", "2026-06-15T18:00"])
            self.assertEqual(raised.exception.code, 2)
            run_accli.assert_not_called()

    def test_events_passes_narrow_query_arguments_to_accli(self) -> None:
        with patch("maccli.calendar.run_accli", return_value=0) as run_accli:
            self.assertEqual(
                self.run_main(
                    [
                        "events",
                        "--calendar",
                        "Work",
                        "--calendar-id",
                        "CAL_ID",
                        "--from",
                        "2026-06-15T09:00",
                        "--to",
                        "2026-06-15T18:00",
                        "--max",
                        "10",
                        "--query",
                        "review",
                    ]
                ),
                0,
            )
            run_accli.assert_called_once_with(
                [
                    "events",
                    "Work",
                    "--calendar-id",
                    "CAL_ID",
                    "--from",
                    "2026-06-15T09:00",
                    "--to",
                    "2026-06-15T18:00",
                    "--max",
                    "10",
                    "--query",
                    "review",
                    "--json",
                ]
            )

    def test_confirmed_create_passes_write_arguments_to_accli(self) -> None:
        with patch("maccli.calendar.run_accli", return_value=0) as run_accli:
            self.assertEqual(
                self.run_main(
                    [
                        "create",
                        "--calendar",
                        "Work",
                        "--calendar-id",
                        "CAL_ID",
                        "--summary",
                        "Project review",
                        "--start",
                        "2026-06-15T14:00",
                        "--end",
                        "2026-06-15T15:00",
                        "--location",
                        "Room A",
                        "--description",
                        "Discuss launch",
                        "--all-day",
                        "--confirm",
                    ]
                ),
                0,
            )
            run_accli.assert_called_once_with(
                [
                    "create",
                    "Work",
                    "--summary",
                    "Project review",
                    "--start",
                    "2026-06-15T14:00",
                    "--end",
                    "2026-06-15T15:00",
                    "--calendar-id",
                    "CAL_ID",
                    "--location",
                    "Room A",
                    "--description",
                    "Discuss launch",
                    "--all-day",
                    "--json",
                ]
            )


if __name__ == "__main__":
    unittest.main()
