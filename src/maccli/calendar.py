#!/usr/bin/env python3
"""Safe wrapper around accli for Apple Calendar queries and guarded writes."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from typing import Iterable


ACCLI_PACKAGE = "@joargp/accli"
INSTALL_HINT = f"Install with: npm install -g {ACCLI_PACKAGE}"


def accli_path() -> str | None:
    return shutil.which("accli")


def require_accli() -> str:
    path = accli_path()
    if path:
        return path
    print("accli was not found on PATH.", file=sys.stderr)
    print(INSTALL_HINT, file=sys.stderr)
    sys.exit(127)


def install_accli() -> int:
    npm = shutil.which("npm")
    if not npm:
        print("npm was not found on PATH.", file=sys.stderr)
        print(INSTALL_HINT, file=sys.stderr)
        return 127

    print(f"Installing {ACCLI_PACKAGE} with npm...", file=sys.stderr)
    completed = subprocess.run([npm, "install", "-g", ACCLI_PACKAGE], text=True)
    if completed.returncode != 0:
        return completed.returncode

    path = accli_path()
    result = {
        "status": "installed" if path else "install_completed_but_not_on_path",
        "accli": path,
        "install_hint": INSTALL_HINT,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if path else 127


def run_accli(args: Iterable[str]) -> int:
    binary = require_accli()
    cmd = [binary, *args]
    completed = subprocess.run(cmd, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


def require_confirmation(args: argparse.Namespace, operation: str) -> int | None:
    if args.confirm:
        return None
    print(f"{operation} modifies Apple Calendar. Re-run with --confirm after user confirmation.", file=sys.stderr)
    return 2


def add_calendar_selector(cmd: list[str], args: argparse.Namespace) -> None:
    if args.calendar_id:
        cmd.extend(["--calendar-id", args.calendar_id])


def doctor(_: argparse.Namespace) -> int:
    info = {
        "platform": platform.system(),
        "is_macos": platform.system() == "Darwin",
        "accli": accli_path(),
        "install_hint": INSTALL_HINT,
    }
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info["is_macos"] and info["accli"] else 1


def setup(_: argparse.Namespace) -> int:
    if platform.system() != "Darwin":
        print("macos-calendar requires macOS.", file=sys.stderr)
        return 1

    path = accli_path()
    if path:
        print(json.dumps({"status": "ready", "accli": path}, ensure_ascii=False, indent=2))
        return 0

    return install_accli()


def calendars(_: argparse.Namespace) -> int:
    return run_accli(["calendars", "--json"])


def events(args: argparse.Namespace) -> int:
    cmd = ["events", args.calendar]
    if args.calendar_id:
        cmd.extend(["--calendar-id", args.calendar_id])
    if args.from_time:
        cmd.extend(["--from", args.from_time])
    if args.to_time:
        cmd.extend(["--to", args.to_time])
    if args.max is not None:
        cmd.extend(["--max", str(args.max)])
    if args.query:
        cmd.extend(["--query", args.query])
    cmd.append("--json")
    return run_accli(cmd)


def event(args: argparse.Namespace) -> int:
    cmd = ["event", args.calendar, args.event_id]
    if args.calendar_id:
        cmd.extend(["--calendar-id", args.calendar_id])
    cmd.append("--json")
    return run_accli(cmd)


def freebusy(args: argparse.Namespace) -> int:
    cmd = ["freebusy"]
    for calendar in args.calendar:
        cmd.extend(["--calendar", calendar])
    for calendar_id in args.calendar_id:
        cmd.extend(["--calendar-id", calendar_id])
    cmd.extend(["--from", args.from_time, "--to", args.to_time, "--json"])
    return run_accli(cmd)


def config_show(_: argparse.Namespace) -> int:
    return run_accli(["config", "show"])


def create_event(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "create")) is not None:
        return error_code

    cmd = [
        "create",
        args.calendar,
        "--summary",
        args.summary,
        "--start",
        args.start_time,
        "--end",
        args.end_time,
    ]
    add_calendar_selector(cmd, args)
    if args.location is not None:
        cmd.extend(["--location", args.location])
    if args.description is not None:
        cmd.extend(["--description", args.description])
    if args.all_day:
        cmd.append("--all-day")
    cmd.append("--json")
    return run_accli(cmd)


def update_event(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "update")) is not None:
        return error_code

    cmd = ["update", args.calendar, args.event_id]
    add_calendar_selector(cmd, args)
    if args.summary is not None:
        cmd.extend(["--summary", args.summary])
    if args.start_time is not None:
        cmd.extend(["--start", args.start_time])
    if args.end_time is not None:
        cmd.extend(["--end", args.end_time])
    if args.location is not None:
        cmd.extend(["--location", args.location])
    if args.description is not None:
        cmd.extend(["--description", args.description])
    if args.all_day:
        cmd.append("--all-day")
    if args.no_all_day:
        cmd.append("--no-all-day")
    cmd.append("--json")
    return run_accli(cmd)


def delete_event(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "delete")) is not None:
        return error_code

    cmd = ["delete", args.calendar, args.event_id]
    add_calendar_selector(cmd, args)
    cmd.append("--json")
    return run_accli(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maccli calendar",
        description="Read and safely modify local Apple Calendar data through accli.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check macOS and accli availability")
    doctor_parser.set_defaults(func=doctor)

    setup_parser = subparsers.add_parser("setup", help="Install accli if needed and verify availability")
    setup_parser.set_defaults(func=setup)

    calendars_parser = subparsers.add_parser("calendars", help="List available calendars as JSON")
    calendars_parser.set_defaults(func=calendars)

    events_parser = subparsers.add_parser("events", help="List events for a calendar as JSON")
    events_parser.add_argument("--calendar", required=True, help="Calendar name")
    events_parser.add_argument("--calendar-id", help="Persistent calendar ID")
    events_parser.add_argument("--from", dest="from_time", help="Start datetime, for example 2026-06-05T09:00")
    events_parser.add_argument("--to", dest="to_time", help="End datetime, for example 2026-06-05T18:00")
    events_parser.add_argument("--max", type=int, help="Maximum events to return")
    events_parser.add_argument("--query", help="Case-insensitive search over event text")
    events_parser.set_defaults(func=events)

    event_parser = subparsers.add_parser("event", help="Read one event by ID as JSON")
    event_parser.add_argument("--calendar", required=True, help="Calendar name")
    event_parser.add_argument("--calendar-id", help="Persistent calendar ID")
    event_parser.add_argument("--event-id", required=True, help="Event ID")
    event_parser.set_defaults(func=event)

    freebusy_parser = subparsers.add_parser("freebusy", help="Check busy slots as JSON")
    freebusy_parser.add_argument("--calendar", action="append", default=[], help="Calendar name; repeatable")
    freebusy_parser.add_argument("--calendar-id", action="append", default=[], help="Persistent calendar ID; repeatable")
    freebusy_parser.add_argument("--from", dest="from_time", required=True, help="Start datetime")
    freebusy_parser.add_argument("--to", dest="to_time", required=True, help="End datetime")
    freebusy_parser.set_defaults(func=freebusy)

    config_parser = subparsers.add_parser("config-show", help="Show accli default calendar config")
    config_parser.set_defaults(func=config_show)

    create_parser = subparsers.add_parser("create", help="Create an event after explicit confirmation")
    create_parser.add_argument("--calendar", required=True, help="Calendar name")
    create_parser.add_argument("--calendar-id", help="Persistent calendar ID")
    create_parser.add_argument("--summary", required=True, help="Event title")
    create_parser.add_argument("--start", dest="start_time", required=True, help="Start datetime")
    create_parser.add_argument("--end", dest="end_time", required=True, help="End datetime")
    create_parser.add_argument("--location", help="Event location")
    create_parser.add_argument("--description", help="Event description")
    create_parser.add_argument("--all-day", action="store_true", help="Create an all-day event")
    create_parser.add_argument("--confirm", action="store_true", help="Confirm the user approved this write")
    create_parser.set_defaults(func=create_event)

    update_parser = subparsers.add_parser("update", help="Update an event after explicit confirmation")
    update_parser.add_argument("--calendar", required=True, help="Calendar name")
    update_parser.add_argument("--calendar-id", help="Persistent calendar ID")
    update_parser.add_argument("--event-id", required=True, help="Event ID")
    update_parser.add_argument("--summary", help="New event title")
    update_parser.add_argument("--start", dest="start_time", help="New start datetime")
    update_parser.add_argument("--end", dest="end_time", help="New end datetime")
    update_parser.add_argument("--location", help="New location")
    update_parser.add_argument("--description", help="New description")
    all_day_group = update_parser.add_mutually_exclusive_group()
    all_day_group.add_argument("--all-day", action="store_true", help="Convert to an all-day event")
    all_day_group.add_argument("--no-all-day", action="store_true", help="Convert to a timed event")
    update_parser.add_argument("--confirm", action="store_true", help="Confirm the user approved this write")
    update_parser.set_defaults(func=update_event)

    delete_parser = subparsers.add_parser("delete", help="Delete an event after explicit confirmation")
    delete_parser.add_argument("--calendar", required=True, help="Calendar name")
    delete_parser.add_argument("--calendar-id", help="Persistent calendar ID")
    delete_parser.add_argument("--event-id", required=True, help="Event ID")
    delete_parser.add_argument("--confirm", action="store_true", help="Confirm the user approved this delete")
    delete_parser.set_defaults(func=delete_event)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "freebusy" and not args.calendar and not args.calendar_id:
        parser.error("freebusy requires at least one --calendar or --calendar-id")
    if args.command == "update" and not any(
        [
            args.summary is not None,
            args.start_time is not None,
            args.end_time is not None,
            args.location is not None,
            args.description is not None,
            args.all_day,
            args.no_all_day,
        ]
    ):
        parser.error("update requires at least one field to change")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
