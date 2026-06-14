#!/usr/bin/env python3
"""Safe wrapper for local macOS Reminders data."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from string import Template
from typing import Any


PERMISSION_HINT = (
    "Grant Automation/Reminders access to the terminal or Codex app in "
    "System Settings > Privacy & Security, then retry."
)
DEFAULT_FILTERED_SCAN_LIMIT = 500
DEFAULT_WRITE_TIMEOUT = 240


COMMON_APPLESCRIPT = r'''
on replaceText(theText, searchString, replacementString)
	set AppleScript's text item delimiters to searchString
	set theItems to every text item of theText
	set AppleScript's text item delimiters to replacementString
	set newText to theItems as text
	set AppleScript's text item delimiters to ""
	return newText
end replaceText

on joinList(theList, delimiter)
	set AppleScript's text item delimiters to delimiter
	set joinedText to theList as text
	set AppleScript's text item delimiters to ""
	return joinedText
end joinList

on containsText(theList, theText)
	repeat with itemText in theList
		if (itemText as text) is theText then return true
	end repeat
	return false
end containsText

on asList(valueOrList)
	if class of valueOrList is list then return valueOrList
	return {valueOrList}
end asList

on jsonString(valueText)
	if valueText is missing value then return "null"
	set t to valueText as text
	set t to my replaceText(t, "\\", "\\\\")
	set t to my replaceText(t, quote, "\\" & quote)
	set t to my replaceText(t, linefeed, "\\n")
	set t to my replaceText(t, return, "\\n")
	set t to my replaceText(t, tab, "\\t")
	return quote & t & quote
end jsonString

on jsonBool(valueBool)
	if valueBool then return "true"
	return "false"
end jsonBool

on pad2(n)
	set s to n as text
	if n < 10 then return "0" & s
	return s
end pad2

on jsonDate(valueDate)
	if valueDate is missing value then return "null"
	set y to year of valueDate as integer
	set mo to month of valueDate as integer
	set da to day of valueDate as integer
	set h to hours of valueDate as integer
	set mi to minutes of valueDate as integer
	set se to seconds of valueDate as integer
	return quote & y & "-" & my pad2(mo) & "-" & my pad2(da) & "T" & my pad2(h) & ":" & my pad2(mi) & ":" & my pad2(se) & quote
end jsonDate

using terms from application "Reminders"

on reminderJson(reminderItem)
	set reminderList to (container of reminderItem)
	set reminderId to (id of reminderItem)
	set reminderName to (name of reminderItem)
	set reminderCompleted to (completed of reminderItem)
	set reminderDueDate to (due date of reminderItem)
	set reminderRemindDate to (remind me date of reminderItem)
	set reminderFlagged to (flagged of reminderItem)
	set reminderBody to (body of reminderItem)
	set fields to {}
	set end of fields to quote & "id" & quote & ":" & my jsonString(reminderId)
	set end of fields to quote & "name" & quote & ":" & my jsonString(reminderName)
	set end of fields to quote & "list_name" & quote & ":" & my jsonString(name of reminderList)
	set end of fields to quote & "list_id" & quote & ":" & my jsonString(id of reminderList)
	set end of fields to quote & "completed" & quote & ":" & my jsonBool(reminderCompleted)
	set end of fields to quote & "due_date" & quote & ":" & my jsonDate(reminderDueDate)
	set end of fields to quote & "remind_me_date" & quote & ":" & my jsonDate(reminderRemindDate)
	set end of fields to quote & "flagged" & quote & ":" & my jsonBool(reminderFlagged)
	set end of fields to quote & "body" & quote & ":" & my jsonString(reminderBody)
	return "{" & my joinList(fields, ",") & "}"
end reminderJson

on reminderSummaryJson(reminderItem)
	set reminderList to (container of reminderItem)
	set fields to {}
	set end of fields to quote & "id" & quote & ":" & my jsonString(id of reminderItem)
	set end of fields to quote & "name" & quote & ":" & my jsonString(name of reminderItem)
	set end of fields to quote & "list_name" & quote & ":" & my jsonString(name of reminderList)
	set end of fields to quote & "list_id" & quote & ":" & my jsonString(id of reminderList)
	set end of fields to quote & "completed" & quote & ":" & my jsonBool(completed of reminderItem)
	set end of fields to quote & "flagged" & quote & ":" & my jsonBool(flagged of reminderItem)
	return "{" & my joinList(fields, ",") & "}"
end reminderSummaryJson

on findReminderById(reminderId)
	tell application "Reminders"
		repeat with reminderList in lists
			set reminderMatches to reminders of reminderList whose id is reminderId
			if (count of reminderMatches) is greater than 0 then return item 1 of reminderMatches
		end repeat
		error "Reminder not found: " & reminderId number 404
	end tell
end findReminderById

on findList(listName, listId)
	tell application "Reminders"
		if listId is not "" then
			set listMatches to lists whose id is listId
			if (count of listMatches) is 0 then error "Reminder list not found: " & listId number 404
			return item 1 of listMatches
		end if
		if listName is not "" then
			set listMatches to lists whose name is listName
			if (count of listMatches) is 0 then error "Reminder list not found: " & listName number 404
			return item 1 of listMatches
		end if
		error "A reminder list name or ID is required." number 400
	end tell
end findList

end using terms from
'''


LISTS_SCRIPT = COMMON_APPLESCRIPT + r'''
tell application "Reminders"
	set jsonItems to {}
	repeat with reminderList in lists
		set listName to name of reminderList as text
		set listId to id of reminderList as text
		set totalCount to count reminders of reminderList
		set incompleteCount to count reminders of reminderList whose completed is false
		set completedCount to totalCount - incompleteCount
		set itemJson to "{" & ¬
			quote & "name" & quote & ":" & my jsonString(listName) & "," & ¬
			quote & "id" & quote & ":" & my jsonString(listId) & "," & ¬
			quote & "incomplete" & quote & ":" & incompleteCount & "," & ¬
			quote & "completed" & quote & ":" & completedCount & "," & ¬
			quote & "total" & quote & ":" & totalCount & ¬
			"}"
		set end of jsonItems to itemJson
	end repeat
	return "[" & my joinList(jsonItems, ",") & "]"
end tell
'''


TODOS_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetListNames : $target_list_names
property targetListIds : $target_list_ids
property completedMode : "$completed_mode"
property includeBody : $include_body
property includeDueDate : $include_due_date
property includeFlagged : $include_flagged
property includeRemindDate : $include_remind_date
property includeCompletionDate : $include_completion_date
property scanLimit : $scan_limit

on shouldReadList(listName, listId)
	if (count of targetListNames) is 0 and (count of targetListIds) is 0 then return true
	if my containsText(targetListNames, listName) then return true
	if my containsText(targetListIds, listId) then return true
	return false
end shouldReadList

tell application "Reminders"
	set jsonItems to {}
	set itemCount to 0
	repeat with reminderList in lists
		set listName to name of reminderList as text
		set listId to id of reminderList as text
		if my shouldReadList(listName, listId) then
			if completedMode is "incomplete" then
				set reminderItems to a reference to reminders of reminderList whose completed is false
			else if completedMode is "completed" then
				set reminderItems to a reference to reminders of reminderList whose completed is true
			else
				set reminderItems to a reference to reminders of reminderList
			end if
			set reminderCount to count of reminderItems
			if reminderCount > 0 then
				set reminderIds to my asList(id of reminderItems)
				set reminderNames to my asList(name of reminderItems)
				set reminderCompletedValues to my asList(completed of reminderItems)
				if includeDueDate then set reminderDueDates to my asList(due date of reminderItems)
				if includeFlagged then set reminderFlaggedValues to my asList(flagged of reminderItems)
				if includeRemindDate then set reminderRemindDates to my asList(remind me date of reminderItems)
				if includeCompletionDate then set reminderCompletionDates to my asList(completion date of reminderItems)
				if includeBody then set reminderBodies to my asList(body of reminderItems)
			end if
			repeat with reminderIndex from 1 to reminderCount
				set fields to {}
				set end of fields to quote & "id" & quote & ":" & my jsonString(item reminderIndex of reminderIds)
				set end of fields to quote & "name" & quote & ":" & my jsonString(item reminderIndex of reminderNames)
				set end of fields to quote & "list_name" & quote & ":" & my jsonString(listName)
				set end of fields to quote & "list_id" & quote & ":" & my jsonString(listId)
				set end of fields to quote & "completed" & quote & ":" & my jsonBool(item reminderIndex of reminderCompletedValues)
				if includeDueDate then
					set end of fields to quote & "due_date" & quote & ":" & my jsonDate(item reminderIndex of reminderDueDates)
				end if
				if includeFlagged then
					set end of fields to quote & "flagged" & quote & ":" & my jsonBool(item reminderIndex of reminderFlaggedValues)
				end if
				if includeRemindDate then
					set end of fields to quote & "remind_me_date" & quote & ":" & my jsonDate(item reminderIndex of reminderRemindDates)
				end if
				if includeCompletionDate then
					set end of fields to quote & "completion_date" & quote & ":" & my jsonDate(item reminderIndex of reminderCompletionDates)
				end if
				if includeBody then
					set end of fields to quote & "body" & quote & ":" & my jsonString(item reminderIndex of reminderBodies)
				end if
				set end of jsonItems to "{" & my joinList(fields, ",") & "}"
				set itemCount to itemCount + 1
				if scanLimit > 0 and itemCount >= scanLimit then exit repeat
			end repeat
		end if
		if scanLimit > 0 and itemCount >= scanLimit then exit repeat
	end repeat
	return "[" & my joinList(jsonItems, ",") & "]"
end tell
'''
)


TODO_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetReminderId : $reminder_id

set targetReminder to my findReminderById(targetReminderId)
return my reminderJson(targetReminder)
'''
)


CREATE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetListName : $list_name
property targetListId : $list_id
property reminderTitle : $title
property reminderBody : $body
property shouldSetBody : $should_set_body
property shouldSetDueDate : $should_set_due_date
property shouldSetRemindDate : $should_set_remind_date
property shouldSetFlagged : $should_set_flagged
property reminderFlagged : $flagged

$due_date_assignment
$remind_date_assignment

set targetList to my findList(targetListName, targetListId)
tell application "Reminders"
	set newReminder to make new reminder at end of reminders of targetList with properties {name:reminderTitle}
	if shouldSetBody then set body of newReminder to reminderBody
	if shouldSetDueDate then set due date of newReminder to dueDateValue
	if shouldSetRemindDate then set remind me date of newReminder to remindDateValue
	if shouldSetFlagged then set flagged of newReminder to reminderFlagged
	return my reminderSummaryJson(newReminder)
end tell
'''
)


UPDATE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetReminderId : $reminder_id
property reminderTitle : $title
property reminderBody : $body
property shouldSetTitle : $should_set_title
property shouldSetBody : $should_set_body
property shouldSetDueDate : $should_set_due_date
property shouldClearDueDate : $should_clear_due_date
property shouldSetRemindDate : $should_set_remind_date
property shouldClearRemindDate : $should_clear_remind_date
property shouldSetFlagged : $should_set_flagged
property reminderFlagged : $flagged

$due_date_assignment
$remind_date_assignment

set targetReminder to my findReminderById(targetReminderId)
tell application "Reminders"
	if shouldSetTitle then set name of targetReminder to reminderTitle
	if shouldSetBody then set body of targetReminder to reminderBody
	if shouldSetDueDate then set due date of targetReminder to dueDateValue
	if shouldClearDueDate then set due date of targetReminder to missing value
	if shouldSetRemindDate then set remind me date of targetReminder to remindDateValue
	if shouldClearRemindDate then set remind me date of targetReminder to missing value
	if shouldSetFlagged then set flagged of targetReminder to reminderFlagged
	return my reminderSummaryJson(targetReminder)
end tell
'''
)


COMPLETE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetReminderId : $reminder_id
property targetCompleted : $completed

set targetReminder to my findReminderById(targetReminderId)
tell application "Reminders"
	set completed of targetReminder to targetCompleted
	return my reminderSummaryJson(targetReminder)
end tell
'''
)


MOVE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetReminderId : $reminder_id
property destinationListName : $to_list
property destinationListId : $to_list_id

set targetReminder to my findReminderById(targetReminderId)
set destinationList to my findList(destinationListName, destinationListId)
tell application "Reminders"
	set originalName to name of targetReminder
	set originalBody to body of targetReminder
	set originalDueDate to due date of targetReminder
	set originalRemindDate to remind me date of targetReminder
	set originalFlagged to flagged of targetReminder
	set originalCompleted to completed of targetReminder
	set movedReminder to make new reminder at end of reminders of destinationList with properties {name:originalName}
	if originalBody is not missing value then set body of movedReminder to originalBody
	if originalDueDate is not missing value then set due date of movedReminder to originalDueDate
	if originalRemindDate is not missing value then set remind me date of movedReminder to originalRemindDate
	set flagged of movedReminder to originalFlagged
	set completed of movedReminder to originalCompleted
	delete targetReminder
	return my reminderSummaryJson(movedReminder)
end tell
'''
)


DELETE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetReminderId : $reminder_id

set targetReminder to my findReminderById(targetReminderId)
tell application "Reminders"
	set reminderName to name of targetReminder as text
	set reminderList to container of targetReminder
	set reminderListName to name of reminderList as text
	set reminderListId to id of reminderList as text
	delete targetReminder
	return "{" & ¬
		quote & "operation" & quote & ":" & my jsonString("delete") & "," & ¬
		quote & "status" & quote & ":" & my jsonString("deleted") & "," & ¬
		quote & "id" & quote & ":" & my jsonString(targetReminderId) & "," & ¬
		quote & "name" & quote & ":" & my jsonString(reminderName) & "," & ¬
		quote & "list_name" & quote & ":" & my jsonString(reminderListName) & "," & ¬
		quote & "list_id" & quote & ":" & my jsonString(reminderListId) & ¬
		"}"
end tell
'''
)


def applescript_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def applescript_list(values: list[str]) -> str:
    return "{" + ", ".join(applescript_quote(value) for value in values) + "}"


def applescript_bool(value: bool) -> str:
    return "true" if value else "false"


def osascript_path() -> str | None:
    return shutil.which("osascript")


def run_osascript(script: str, timeout: int) -> Any:
    binary = osascript_path()
    if not binary:
        raise RuntimeError("osascript was not found on PATH.")
    try:
        completed = subprocess.run(
            [binary],
            input=script,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Reminders operation timed out after {timeout}s. {PERMISSION_HINT}"
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"osascript exited with {completed.returncode}. {PERMISSION_HINT}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse Reminders JSON output: {exc}") from exc


def write_json(value: Any) -> int:
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


def parse_local_datetime(value: str | None, *, date_is_end: bool = False) -> datetime | None:
    if not value:
        return None
    if len(value) == 10:
        parsed_date = date.fromisoformat(value)
        if date_is_end:
            parsed_date += timedelta(days=1)
        return datetime.combine(parsed_date, time.min)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


def applescript_date_assignment(variable_name: str, value: str | None) -> str:
    if value is None:
        return f"set {variable_name} to missing value"
    parsed = parse_local_datetime(value)
    if parsed is None:
        return f"set {variable_name} to missing value"
    seconds = parsed.hour * 3600 + parsed.minute * 60 + parsed.second
    return "\n".join(
        [
            f"set {variable_name} to current date",
            f"set year of {variable_name} to {parsed.year}",
            f"set month of {variable_name} to {parsed.month}",
            f"set day of {variable_name} to {parsed.day}",
            f"set time of {variable_name} to {seconds}",
        ]
    )


def item_dates(item: dict[str, Any], field: str) -> list[datetime]:
    fields = ["due_date"] if field == "due" else ["remind_me_date"] if field == "remind" else ["due_date", "remind_me_date"]
    parsed: list[datetime] = []
    for key in fields:
        value = item.get(key)
        if not value:
            continue
        try:
            parsed.append(parse_local_datetime(value) or datetime.min)
        except ValueError:
            continue
    return parsed


def filter_items(items: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    query = (args.query or "").casefold()
    due_from = parse_local_datetime(args.due_from) if args.due_from else None
    due_to = parse_local_datetime(args.due_to, date_is_end=True) if args.due_to else None
    overdue_before = parse_local_datetime(args.overdue_before) if args.overdue_before else None

    filtered: list[dict[str, Any]] = []
    for item in items:
        if query:
            haystack_values = [item.get("name"), item.get("list_name")]
            if args.include_body:
                haystack_values.append(item.get("body"))
            haystack = "\n".join(str(value) for value in haystack_values if value).casefold()
            if query not in haystack:
                continue

        if due_from or due_to or overdue_before:
            dates = item_dates(item, args.date_field)
            if not dates:
                continue
            if due_from and not any(candidate >= due_from for candidate in dates):
                continue
            if due_to and not any(candidate < due_to for candidate in dates):
                continue
            if overdue_before and not any(candidate < overdue_before for candidate in dates):
                continue

        filtered.append(item)
        if args.max is not None and len(filtered) >= args.max:
            break

    return filtered


def completed_mode(args: argparse.Namespace) -> str:
    if getattr(args, "completed_only", False):
        return "completed"
    if getattr(args, "include_completed", False):
        return "all"
    return "incomplete"


def read_todos(args: argparse.Namespace) -> list[dict[str, Any]]:
    has_date_filter = bool(args.due_from or args.due_to or args.overdue_before)
    has_python_filter = bool(args.query or has_date_filter)
    scan_limit = args.scan_limit
    if scan_limit is None:
        scan_limit = DEFAULT_FILTERED_SCAN_LIMIT if has_python_filter else args.max
    script = TODOS_TEMPLATE.substitute(
        target_list_names=applescript_list(args.list or []),
        target_list_ids=applescript_list(args.list_id or []),
        completed_mode=completed_mode(args),
        include_body=applescript_bool(args.include_body),
        include_due_date=applescript_bool(args.include_due_date or (has_date_filter and args.date_field in {"due", "either"})),
        include_flagged=applescript_bool(args.include_flagged),
        include_remind_date=applescript_bool(args.include_remind_date or (has_date_filter and args.date_field in {"remind", "either"})),
        include_completion_date=applescript_bool(args.include_completion_date or args.completed_only),
        scan_limit=scan_limit,
    )
    items = run_osascript(script, args.timeout)
    return filter_items(items, args)


def require_confirmation(args: argparse.Namespace, operation: str) -> int | None:
    if args.confirm:
        return None
    print(f"{operation} modifies Apple Reminders. Re-run with --confirm after user confirmation.", file=sys.stderr)
    return 2


def doctor(args: argparse.Namespace) -> int:
    info: dict[str, Any] = {
        "platform": platform.system(),
        "is_macos": platform.system() == "Darwin",
        "osascript": osascript_path(),
        "permission_hint": PERMISSION_HINT,
    }
    if args.probe:
        try:
            lists = run_osascript(LISTS_SCRIPT, args.timeout)
            info["can_read_reminders"] = True
            info["list_count"] = len(lists)
        except RuntimeError as exc:
            info["can_read_reminders"] = False
            info["error"] = str(exc)
    write_json(info)
    return 0 if info["is_macos"] and info["osascript"] and info.get("can_read_reminders", True) else 1


def lists(args: argparse.Namespace) -> int:
    return write_json(run_osascript(LISTS_SCRIPT, args.timeout))


def todos(args: argparse.Namespace) -> int:
    return write_json(read_todos(args))


def todo(args: argparse.Namespace) -> int:
    script = TODO_TEMPLATE.substitute(reminder_id=applescript_quote(args.reminder_id))
    return write_json(run_osascript(script, args.timeout))


def today(args: argparse.Namespace) -> int:
    today_date = date.today()
    args.due_from = today_date.isoformat()
    args.due_to = (today_date + timedelta(days=1)).isoformat()
    return write_json(read_todos(args))


def overdue(args: argparse.Namespace) -> int:
    args.overdue_before = datetime.now().isoformat(timespec="seconds")
    return write_json(read_todos(args))


def create_todo(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "create")) is not None:
        return error_code
    script = CREATE_TEMPLATE.substitute(
        list_name=applescript_quote(args.list or ""),
        list_id=applescript_quote(args.list_id or ""),
        title=applescript_quote(args.title),
        body=applescript_quote(args.body or ""),
        should_set_body=applescript_bool(args.body is not None),
        should_set_due_date=applescript_bool(args.due is not None),
        should_set_remind_date=applescript_bool(args.remind_at is not None),
        should_set_flagged=applescript_bool(args.flagged),
        flagged=applescript_bool(args.flagged),
        due_date_assignment=applescript_date_assignment("dueDateValue", args.due),
        remind_date_assignment=applescript_date_assignment("remindDateValue", args.remind_at),
    )
    return write_json(run_osascript(script, args.timeout))


def update_todo(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "update")) is not None:
        return error_code
    script = UPDATE_TEMPLATE.substitute(
        reminder_id=applescript_quote(args.reminder_id),
        title=applescript_quote(args.title or ""),
        body=applescript_quote(args.body or ""),
        should_set_title=applescript_bool(args.title is not None),
        should_set_body=applescript_bool(args.body is not None),
        should_set_due_date=applescript_bool(args.due is not None),
        should_clear_due_date=applescript_bool(args.clear_due),
        should_set_remind_date=applescript_bool(args.remind_at is not None),
        should_clear_remind_date=applescript_bool(args.clear_remind_at),
        should_set_flagged=applescript_bool(args.flagged or args.no_flagged),
        flagged=applescript_bool(args.flagged),
        due_date_assignment=applescript_date_assignment("dueDateValue", args.due),
        remind_date_assignment=applescript_date_assignment("remindDateValue", args.remind_at),
    )
    return write_json(run_osascript(script, args.timeout))


def set_completed(args: argparse.Namespace, *, completed: bool) -> int:
    operation = "complete" if completed else "uncomplete"
    if (error_code := require_confirmation(args, operation)) is not None:
        return error_code
    script = COMPLETE_TEMPLATE.substitute(
        reminder_id=applescript_quote(args.reminder_id),
        completed=applescript_bool(completed),
    )
    return write_json(run_osascript(script, args.timeout))


def complete_todo(args: argparse.Namespace) -> int:
    return set_completed(args, completed=True)


def uncomplete_todo(args: argparse.Namespace) -> int:
    return set_completed(args, completed=False)


def move_todo(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "move")) is not None:
        return error_code
    script = MOVE_TEMPLATE.substitute(
        reminder_id=applescript_quote(args.reminder_id),
        to_list=applescript_quote(args.to_list or ""),
        to_list_id=applescript_quote(args.to_list_id or ""),
    )
    return write_json(run_osascript(script, args.timeout))


def delete_todo(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "delete")) is not None:
        return error_code
    script = DELETE_TEMPLATE.substitute(reminder_id=applescript_quote(args.reminder_id))
    return write_json(run_osascript(script, args.timeout))


def add_common_todo_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--list", action="append", default=[], help="Reminder list name; repeatable")
    parser.add_argument("--list-id", action="append", default=[], help="Reminder list ID; repeatable")
    parser.add_argument("--include-completed", action="store_true", help="Include completed reminders")
    parser.add_argument("--completed-only", action="store_true", help="Read only completed reminders")
    parser.add_argument("--include-body", action="store_true", help="Include reminder notes/body text")
    parser.add_argument("--include-due-date", action="store_true", help="Include due date")
    parser.add_argument("--include-flagged", action="store_true", help="Include flagged status")
    parser.add_argument("--include-remind-date", action="store_true", help="Include remind-me date")
    parser.add_argument("--include-completion-date", action="store_true", help="Include completion date")
    parser.add_argument("--query", help="Case-insensitive search over title, list name, and body when included")
    parser.add_argument("--due-from", help="Start datetime or date, for example 2026-06-15 or 2026-06-15T09:00")
    parser.add_argument("--due-to", help="End datetime or date; date-only values are exclusive next midnight")
    parser.add_argument("--overdue-before", help=argparse.SUPPRESS)
    parser.add_argument("--date-field", choices=["due", "remind", "either"], default="due", help="Date field for filters")
    parser.add_argument("--max", type=int, default=50, help="Maximum matching reminders to return")
    parser.add_argument("--scan-limit", type=int, help="Maximum reminders to scan before Python filtering")
    parser.add_argument("--timeout", type=int, default=120, help="osascript timeout in seconds")


def add_reminder_id_arg(parser: argparse.ArgumentParser, *, timeout_default: int = 120) -> None:
    parser.add_argument("--reminder-id", required=True, help="Reminder ID")
    parser.add_argument("--timeout", type=int, default=timeout_default, help="osascript timeout in seconds")


def add_confirm_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--confirm", action="store_true", help="Confirm the user approved this write")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maccli reminders",
        description="Read and safely modify local macOS Reminders data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check macOS, osascript, and optionally Reminders access")
    doctor_parser.add_argument("--probe", action="store_true", help="Try a read-only Reminders list probe")
    doctor_parser.add_argument("--timeout", type=int, default=30, help="osascript timeout in seconds")
    doctor_parser.set_defaults(func=doctor)

    lists_parser = subparsers.add_parser("lists", help="List Reminders lists and counts as JSON")
    lists_parser.add_argument("--timeout", type=int, default=60, help="osascript timeout in seconds")
    lists_parser.set_defaults(func=lists)

    todos_parser = subparsers.add_parser("todos", help="Read reminders as JSON")
    add_common_todo_args(todos_parser)
    todos_parser.set_defaults(func=todos)

    todo_parser = subparsers.add_parser("todo", help="Read one reminder by ID as JSON")
    add_reminder_id_arg(todo_parser)
    todo_parser.set_defaults(func=todo)

    today_parser = subparsers.add_parser("today", help="Read incomplete reminders due today")
    add_common_todo_args(today_parser)
    today_parser.set_defaults(func=today)

    overdue_parser = subparsers.add_parser("overdue", help="Read incomplete reminders due before now")
    add_common_todo_args(overdue_parser)
    overdue_parser.set_defaults(func=overdue)

    search_parser = subparsers.add_parser("search", help="Search reminders by title/list/body")
    add_common_todo_args(search_parser)
    search_parser.add_argument("query_text", help="Search query")
    search_parser.set_defaults(func=lambda args: (setattr(args, "query", args.query_text), todos(args))[1])

    create_parser = subparsers.add_parser("create", help="Create a reminder after explicit confirmation")
    list_group = create_parser.add_mutually_exclusive_group(required=True)
    list_group.add_argument("--list", help="Reminder list name")
    list_group.add_argument("--list-id", help="Reminder list ID")
    create_parser.add_argument("--title", required=True, help="Reminder title")
    create_parser.add_argument("--body", help="Reminder notes/body text")
    create_parser.add_argument("--due", help="Due datetime or date")
    create_parser.add_argument("--remind-at", help="Remind-me datetime or date")
    create_parser.add_argument("--flagged", action="store_true", help="Create as flagged")
    create_parser.add_argument("--timeout", type=int, default=DEFAULT_WRITE_TIMEOUT, help="osascript timeout in seconds")
    add_confirm_arg(create_parser)
    create_parser.set_defaults(func=create_todo)

    update_parser = subparsers.add_parser("update", help="Update a reminder after explicit confirmation")
    add_reminder_id_arg(update_parser, timeout_default=DEFAULT_WRITE_TIMEOUT)
    update_parser.add_argument("--title", help="New reminder title")
    update_parser.add_argument("--body", help="New reminder notes/body text")
    due_group = update_parser.add_mutually_exclusive_group()
    due_group.add_argument("--due", help="New due datetime or date")
    due_group.add_argument("--clear-due", action="store_true", help="Clear due date")
    remind_group = update_parser.add_mutually_exclusive_group()
    remind_group.add_argument("--remind-at", help="New remind-me datetime or date")
    remind_group.add_argument("--clear-remind-at", action="store_true", help="Clear remind-me date")
    flagged_group = update_parser.add_mutually_exclusive_group()
    flagged_group.add_argument("--flagged", action="store_true", help="Set flagged")
    flagged_group.add_argument("--no-flagged", action="store_true", help="Clear flagged")
    add_confirm_arg(update_parser)
    update_parser.set_defaults(func=update_todo)

    complete_parser = subparsers.add_parser("complete", help="Mark a reminder completed after explicit confirmation")
    add_reminder_id_arg(complete_parser, timeout_default=DEFAULT_WRITE_TIMEOUT)
    add_confirm_arg(complete_parser)
    complete_parser.set_defaults(func=complete_todo)

    uncomplete_parser = subparsers.add_parser("uncomplete", help="Mark a reminder incomplete after explicit confirmation")
    add_reminder_id_arg(uncomplete_parser, timeout_default=DEFAULT_WRITE_TIMEOUT)
    add_confirm_arg(uncomplete_parser)
    uncomplete_parser.set_defaults(func=uncomplete_todo)

    move_parser = subparsers.add_parser("move", help="Move a reminder to another list after explicit confirmation")
    add_reminder_id_arg(move_parser, timeout_default=DEFAULT_WRITE_TIMEOUT)
    destination_group = move_parser.add_mutually_exclusive_group(required=True)
    destination_group.add_argument("--to-list", help="Destination list name")
    destination_group.add_argument("--to-list-id", help="Destination list ID")
    add_confirm_arg(move_parser)
    move_parser.set_defaults(func=move_todo)

    delete_parser = subparsers.add_parser("delete", help="Delete a reminder after explicit confirmation")
    add_reminder_id_arg(delete_parser, timeout_default=DEFAULT_WRITE_TIMEOUT)
    add_confirm_arg(delete_parser)
    delete_parser.set_defaults(func=delete_todo)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "include_completed", False) and getattr(args, "completed_only", False):
        parser.error("--include-completed and --completed-only are mutually exclusive")
    if args.command == "update" and not any(
        [
            args.title is not None,
            args.body is not None,
            args.due is not None,
            args.clear_due,
            args.remind_at is not None,
            args.clear_remind_at,
            args.flagged,
            args.no_flagged,
        ]
    ):
        parser.error("update requires at least one field to change")
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
