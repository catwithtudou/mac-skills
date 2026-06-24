#!/usr/bin/env python3
"""Safe wrapper for local macOS Notes data."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from string import Template
from typing import Any


PERMISSION_HINT = (
    "Grant Automation/Notes access to the terminal or AI agent app in "
    "System Settings > Privacy & Security, then retry."
)
DEFAULT_READ_TIMEOUT = 120
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

on textContains(haystack, needle)
	if needle is "" then return true
	if haystack is missing value then return false
	set haystackText to haystack as text
	ignoring case
		if haystackText contains needle then return true
	end ignoring
	return false
end textContains

using terms from application "Notes"

on accountJson(accountItem)
	set accountObject to contents of accountItem
	set fields to {}
	set accountName to (name of accountObject) as text
	set accountId to (id of accountObject) as text
	tell application "Notes" to set folderCount to count folders of accountObject
	set end of fields to quote & "name" & quote & ":" & my jsonString(accountName)
	set end of fields to quote & "id" & quote & ":" & my jsonString(accountId)
	set end of fields to quote & "folder_count" & quote & ":" & folderCount
	return "{" & my joinList(fields, ",") & "}"
end accountJson

on folderJson(folderItem, accountItem)
	set folderObject to contents of folderItem
	set accountObject to contents of accountItem
	set fields to {}
	set folderName to (name of folderObject) as text
	set folderId to (id of folderObject) as text
	set accountName to (name of accountObject) as text
	set accountId to (id of accountObject) as text
	tell application "Notes" to set noteCount to count notes of folderObject
	set end of fields to quote & "name" & quote & ":" & my jsonString(folderName)
	set end of fields to quote & "id" & quote & ":" & my jsonString(folderId)
	set end of fields to quote & "account_name" & quote & ":" & my jsonString(accountName)
	set end of fields to quote & "account_id" & quote & ":" & my jsonString(accountId)
	set end of fields to quote & "note_count" & quote & ":" & noteCount
	return "{" & my joinList(fields, ",") & "}"
end folderJson

on noteJson(noteItem, folderItem, accountItem, includeBody)
	set noteObject to contents of noteItem
	set folderObject to contents of folderItem
	set accountObject to contents of accountItem
	set fields to {}
	set noteId to (id of noteObject) as text
	set noteName to (name of noteObject) as text
	set folderName to (name of folderObject) as text
	set folderId to (id of folderObject) as text
	set accountName to (name of accountObject) as text
	set accountId to (id of accountObject) as text
	set end of fields to quote & "id" & quote & ":" & my jsonString(noteId)
	set end of fields to quote & "name" & quote & ":" & my jsonString(noteName)
	set end of fields to quote & "folder_name" & quote & ":" & my jsonString(folderName)
	set end of fields to quote & "folder_id" & quote & ":" & my jsonString(folderId)
	set end of fields to quote & "account_name" & quote & ":" & my jsonString(accountName)
	set end of fields to quote & "account_id" & quote & ":" & my jsonString(accountId)
	set end of fields to quote & "creation_date" & quote & ":" & my jsonDate(creation date of noteObject)
	set end of fields to quote & "modification_date" & quote & ":" & my jsonDate(modification date of noteObject)
	if includeBody then
		set noteBody to (body of noteObject) as text
		set end of fields to quote & "body" & quote & ":" & my jsonString(noteBody)
	end if
	return "{" & my joinList(fields, ",") & "}"
end noteJson

on accountMatches(accountItem, accountName, accountId)
	set accountObject to contents of accountItem
	if accountId is not "" then return ((id of accountObject) as text) is accountId
	if accountName is not "" then return ((name of accountObject) as text) is accountName
	return true
end accountMatches

on folderMatches(folderItem, folderName, folderId)
	set folderObject to contents of folderItem
	if folderId is not "" then return ((id of folderObject) as text) is folderId
	if folderName is not "" then return ((name of folderObject) as text) is folderName
	return true
end folderMatches

on findFolder(accountName, accountId, folderName, folderId)
	if folderName is "" and folderId is "" then error "A Notes folder name or ID is required." number 400
	if folderName is not "" and accountName is "" and accountId is "" then error "A Notes account name or ID is required when selecting a folder by name." number 400
	tell application "Notes"
		repeat with accountItem in accounts
			if my accountMatches(accountItem, accountName, accountId) then
				repeat with folderItem in folders of accountItem
					if my folderMatches(folderItem, folderName, folderId) then return {folderItem, accountItem}
				end repeat
			end if
		end repeat
		error "Notes folder not found." number 404
	end tell
end findFolder

on findNoteById(noteId)
	tell application "Notes"
		repeat with accountItem in accounts
			repeat with folderItem in folders of accountItem
				set noteMatches to notes of folderItem whose id is noteId
				if (count of noteMatches) is greater than 0 then return {item 1 of noteMatches, folderItem, accountItem}
			end repeat
		end repeat
		error "Note not found: " & noteId number 404
	end tell
end findNoteById

end using terms from
'''


ACCOUNTS_SCRIPT = COMMON_APPLESCRIPT + r'''
tell application "Notes"
	set jsonItems to {}
	repeat with accountItem in accounts
		set end of jsonItems to my accountJson(accountItem)
	end repeat
	return "[" & my joinList(jsonItems, ",") & "]"
end tell
'''


FOLDERS_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetAccountName : $account_name
property targetAccountId : $account_id

tell application "Notes"
	set jsonItems to {}
	repeat with accountItem in accounts
		if my accountMatches(accountItem, targetAccountName, targetAccountId) then
			repeat with folderItem in folders of accountItem
				set end of jsonItems to my folderJson(folderItem, accountItem)
			end repeat
		end if
	end repeat
	return "[" & my joinList(jsonItems, ",") & "]"
end tell
'''
)


LIST_NOTES_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetAccountName : $account_name
property targetAccountId : $account_id
property targetFolderName : $folder_name
property targetFolderId : $folder_id
property includeBody : $include_body
property resultLimit : $limit

set folderResult to my findFolder(targetAccountName, targetAccountId, targetFolderName, targetFolderId)
set targetFolder to item 1 of folderResult
set targetAccount to item 2 of folderResult

tell application "Notes"
	set jsonItems to {}
	set itemCount to 0
	repeat with noteItem in notes of targetFolder
		set end of jsonItems to my noteJson(noteItem, targetFolder, targetAccount, includeBody)
		set itemCount to itemCount + 1
		if resultLimit > 0 and itemCount >= resultLimit then exit repeat
	end repeat
	return "[" & my joinList(jsonItems, ",") & "]"
end tell
'''
)


SEARCH_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetAccountName : $account_name
property targetAccountId : $account_id
property targetFolderName : $folder_name
property targetFolderId : $folder_id
property queryText : $query
property shouldSearchBody : $search_body
property includeBody : $include_body
property resultLimit : $limit
property scanLimit : $scan_limit

tell application "Notes"
	set jsonItems to {}
	set itemCount to 0
	set scannedCount to 0
	repeat with accountItem in accounts
		if my accountMatches(accountItem, targetAccountName, targetAccountId) then
			repeat with folderItem in folders of accountItem
				if my folderMatches(folderItem, targetFolderName, targetFolderId) then
					repeat with noteItem in notes of folderItem
						set searchableText to name of noteItem as text
						if shouldSearchBody then set searchableText to searchableText & linefeed & (body of noteItem as text)
						set scannedCount to scannedCount + 1
						if my textContains(searchableText, queryText) then
							set end of jsonItems to my noteJson(noteItem, folderItem, accountItem, includeBody)
							set itemCount to itemCount + 1
							if resultLimit > 0 and itemCount >= resultLimit then exit repeat
						end if
						if scanLimit > 0 and scannedCount >= scanLimit then exit repeat
					end repeat
				end if
				if (resultLimit > 0 and itemCount >= resultLimit) or (scanLimit > 0 and scannedCount >= scanLimit) then exit repeat
			end repeat
		end if
		if (resultLimit > 0 and itemCount >= resultLimit) or (scanLimit > 0 and scannedCount >= scanLimit) then exit repeat
	end repeat
	return "[" & my joinList(jsonItems, ",") & "]"
end tell
'''
)


NOTE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetNoteId : $note_id
property includeBody : $include_body

set noteResult to my findNoteById(targetNoteId)
set targetNote to item 1 of noteResult
set targetFolder to item 2 of noteResult
set targetAccount to item 3 of noteResult
return my noteJson(targetNote, targetFolder, targetAccount, includeBody)
'''
)


CREATE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetAccountName : $account_name
property targetAccountId : $account_id
property targetFolderName : $folder_name
property targetFolderId : $folder_id
property noteTitle : $title
property noteBody : $body
property shouldSetBody : $should_set_body

set folderResult to my findFolder(targetAccountName, targetAccountId, targetFolderName, targetFolderId)
set targetFolder to item 1 of folderResult
set targetAccount to item 2 of folderResult

tell application "Notes"
	if shouldSetBody then
		set newNote to make new note at targetFolder with properties {name:noteTitle, body:noteBody}
	else
		set newNote to make new note at targetFolder with properties {name:noteTitle}
	end if
	return my noteJson(newNote, targetFolder, targetAccount, false)
end tell
'''
)


DELETE_TEMPLATE = Template(
    COMMON_APPLESCRIPT
    + r'''
property targetNoteId : $note_id

set noteResult to my findNoteById(targetNoteId)
set targetNote to item 1 of noteResult
set targetFolder to item 2 of noteResult
set targetAccount to item 3 of noteResult

tell application "Notes"
	set targetNoteObject to contents of targetNote
	set targetFolderObject to contents of targetFolder
	set targetAccountObject to contents of targetAccount
	set noteName to (name of targetNoteObject) as text
	set folderName to (name of targetFolderObject) as text
	set folderId to (id of targetFolderObject) as text
	set accountName to (name of targetAccountObject) as text
	set accountId to (id of targetAccountObject) as text
	delete targetNoteObject
	return "{" & ¬
		quote & "operation" & quote & ":" & my jsonString("delete") & "," & ¬
		quote & "status" & quote & ":" & my jsonString("deleted") & "," & ¬
		quote & "id" & quote & ":" & my jsonString(targetNoteId) & "," & ¬
		quote & "name" & quote & ":" & my jsonString(noteName) & "," & ¬
		quote & "folder_name" & quote & ":" & my jsonString(folderName) & "," & ¬
		quote & "folder_id" & quote & ":" & my jsonString(folderId) & "," & ¬
		quote & "account_name" & quote & ":" & my jsonString(accountName) & "," & ¬
		quote & "account_id" & quote & ":" & my jsonString(accountId) & ¬
		"}"
end tell
'''
)


def applescript_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


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
        raise RuntimeError(f"Notes operation timed out after {timeout}s. {PERMISSION_HINT}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"osascript exited with {completed.returncode}. {PERMISSION_HINT}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse Notes JSON output: {exc}") from exc


def write_json(value: Any) -> int:
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0


def require_confirmation(args: argparse.Namespace, operation: str) -> int | None:
    if args.confirm:
        return None
    print(f"{operation} modifies Apple Notes. Re-run with --confirm after user confirmation.", file=sys.stderr)
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
            accounts = run_osascript(ACCOUNTS_SCRIPT, args.timeout)
            info["can_read_notes"] = True
            info["account_count"] = len(accounts)
        except RuntimeError as exc:
            info["can_read_notes"] = False
            info["error"] = str(exc)
    write_json(info)
    return 0 if info["is_macos"] and info["osascript"] and info.get("can_read_notes", True) else 1


def accounts(args: argparse.Namespace) -> int:
    return write_json(run_osascript(ACCOUNTS_SCRIPT, args.timeout))


def folders(args: argparse.Namespace) -> int:
    script = FOLDERS_TEMPLATE.substitute(
        account_name=applescript_quote(args.account or ""),
        account_id=applescript_quote(args.account_id or ""),
    )
    return write_json(run_osascript(script, args.timeout))


def list_notes(args: argparse.Namespace) -> int:
    script = LIST_NOTES_TEMPLATE.substitute(
        account_name=applescript_quote(args.account or ""),
        account_id=applescript_quote(args.account_id or ""),
        folder_name=applescript_quote(args.folder or ""),
        folder_id=applescript_quote(args.folder_id or ""),
        include_body=applescript_bool(args.include_body),
        limit=args.max,
    )
    return write_json(run_osascript(script, args.timeout))


def search(args: argparse.Namespace) -> int:
    script = SEARCH_TEMPLATE.substitute(
        account_name=applescript_quote(args.account or ""),
        account_id=applescript_quote(args.account_id or ""),
        folder_name=applescript_quote(args.folder or ""),
        folder_id=applescript_quote(args.folder_id or ""),
        query=applescript_quote(args.query),
        search_body=applescript_bool(args.search_body or args.include_body),
        include_body=applescript_bool(args.include_body),
        limit=args.max,
        scan_limit=args.scan_limit,
    )
    return write_json(run_osascript(script, args.timeout))


def note(args: argparse.Namespace) -> int:
    script = NOTE_TEMPLATE.substitute(
        note_id=applescript_quote(args.note_id),
        include_body=applescript_bool(not args.no_body),
    )
    return write_json(run_osascript(script, args.timeout))


def create_note(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "create")) is not None:
        return error_code
    script = CREATE_TEMPLATE.substitute(
        account_name=applescript_quote(args.account or ""),
        account_id=applescript_quote(args.account_id or ""),
        folder_name=applescript_quote(args.folder or ""),
        folder_id=applescript_quote(args.folder_id or ""),
        title=applescript_quote(args.title),
        body=applescript_quote(args.body or ""),
        should_set_body=applescript_bool(args.body is not None),
    )
    return write_json(run_osascript(script, args.timeout))


def delete_note(args: argparse.Namespace) -> int:
    if (error_code := require_confirmation(args, "delete")) is not None:
        return error_code
    if not args.confirm_delete:
        print(
            "delete is destructive. Re-run with --confirm --confirm-delete after a second user confirmation.",
            file=sys.stderr,
        )
        return 2
    script = DELETE_TEMPLATE.substitute(note_id=applescript_quote(args.note_id))
    return write_json(run_osascript(script, args.timeout))


def add_account_selector(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--account", help="Notes account name")
    group.add_argument("--account-id", help="Notes account ID")


def add_folder_selector(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--folder", help="Notes folder name")
    group.add_argument("--folder-id", help="Notes folder ID")


def add_required_folder_selector(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--folder", help="Notes folder name")
    group.add_argument("--folder-id", help="Notes folder ID")


def add_confirm_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--confirm", action="store_true", help="Confirm the user approved this write")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maccli notes",
        description="Read, search, create, and guarded-delete local Apple Notes data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check macOS, osascript, and optionally Notes access")
    doctor_parser.add_argument("--probe", action="store_true", help="Try a read-only Notes account probe")
    doctor_parser.add_argument("--timeout", type=int, default=30, help="osascript timeout in seconds")
    doctor_parser.set_defaults(func=doctor)

    accounts_parser = subparsers.add_parser("accounts", help="List Notes accounts as JSON")
    accounts_parser.add_argument("--timeout", type=int, default=60, help="osascript timeout in seconds")
    accounts_parser.set_defaults(func=accounts)

    folders_parser = subparsers.add_parser("folders", help="List Notes folders as JSON")
    add_account_selector(folders_parser)
    folders_parser.add_argument("--timeout", type=int, default=DEFAULT_READ_TIMEOUT, help="osascript timeout in seconds")
    folders_parser.set_defaults(func=folders)

    notes_parser = subparsers.add_parser("notes", help="List note summaries from an explicit folder")
    add_account_selector(notes_parser)
    add_required_folder_selector(notes_parser)
    notes_parser.add_argument("--include-body", action="store_true", help="Include note body HTML")
    notes_parser.add_argument("--max", type=int, default=20, help="Maximum notes to return")
    notes_parser.add_argument("--timeout", type=int, default=DEFAULT_READ_TIMEOUT, help="osascript timeout in seconds")
    notes_parser.set_defaults(func=list_notes)

    search_parser = subparsers.add_parser("search", help="Search Notes by title, and body when requested")
    add_account_selector(search_parser)
    add_folder_selector(search_parser)
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--search-body", action="store_true", help="Also scan note body HTML")
    search_parser.add_argument("--include-body", action="store_true", help="Include matched note body HTML")
    search_parser.add_argument("--max", type=int, default=20, help="Maximum matching notes to return")
    search_parser.add_argument("--scan-limit", type=int, default=500, help="Maximum notes to scan")
    search_parser.add_argument("--timeout", type=int, default=DEFAULT_READ_TIMEOUT, help="osascript timeout in seconds")
    search_parser.set_defaults(func=search)

    note_parser = subparsers.add_parser("note", help="Read one note by ID as JSON")
    note_parser.add_argument("--note-id", required=True, help="Note ID")
    note_parser.add_argument("--no-body", action="store_true", help="Return metadata only")
    note_parser.add_argument("--timeout", type=int, default=DEFAULT_READ_TIMEOUT, help="osascript timeout in seconds")
    note_parser.set_defaults(func=note)

    create_parser = subparsers.add_parser("create", help="Create a note after explicit confirmation")
    add_account_selector(create_parser)
    add_required_folder_selector(create_parser)
    create_parser.add_argument("--title", required=True, help="Note title")
    create_parser.add_argument("--body", help="Note body; Apple Notes stores this as HTML-capable content")
    create_parser.add_argument("--timeout", type=int, default=DEFAULT_WRITE_TIMEOUT, help="osascript timeout in seconds")
    add_confirm_arg(create_parser)
    create_parser.set_defaults(func=create_note)

    delete_parser = subparsers.add_parser("delete", help="Delete a note after explicit double confirmation")
    delete_parser.add_argument("--note-id", required=True, help="Note ID")
    delete_parser.add_argument("--timeout", type=int, default=DEFAULT_WRITE_TIMEOUT, help="osascript timeout in seconds")
    add_confirm_arg(delete_parser)
    delete_parser.add_argument("--confirm-delete", action="store_true", help="Confirm the user approved destructive delete")
    delete_parser.set_defaults(func=delete_note)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {"notes", "create"} and args.folder and not (args.account or args.account_id):
        parser.error("--folder requires --account or --account-id")
    try:
        return args.func(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
