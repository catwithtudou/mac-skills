from __future__ import annotations

import sys

from . import calendar, notes, reminders


HELP = """usage: maccli [-h] {calendar,reminders,notes} ...

Local-first macOS app CLI for AI agent skills.

positional arguments:
  {calendar,reminders,notes}
    calendar            Work with Apple Calendar
    reminders           Work with Apple Reminders
    notes               Work with Apple Notes

options:
  -h, --help            show this help message and exit
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(HELP)
        return 0

    app, app_args = args[0], args[1:]
    if app == "calendar":
        return calendar.main(app_args)
    if app == "reminders":
        return reminders.main(app_args)
    if app == "notes":
        return notes.main(app_args)

    print(f"maccli: unknown app: {app}", file=sys.stderr)
    print("Run 'maccli --help' for usage.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
