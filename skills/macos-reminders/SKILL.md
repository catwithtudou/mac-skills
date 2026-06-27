---
name: macos-reminders
version: 0.3.1
description: Read and safely manage local Apple Reminders data on macOS using a bundled launcher backed by local maccli or pinned npm fallback. Use when an AI agent needs to inspect reminder lists, list todos, search reminders, create reminders, update reminders, complete or uncomplete reminders, move reminders between lists, delete reminders, or troubleshoot Reminders permission access.
---

# macOS Reminders

## Quick Start

Use the bundled launcher for Apple Reminders work. It uses local `maccli` when available and falls back to `npx -y mac-skills@0.3.1`. Run commands from this skill directory. Reads may be slow on large Reminders databases; run one Reminders command at a time.

```bash
python3 scripts/read_reminders.py doctor --probe
python3 scripts/read_reminders.py lists
python3 scripts/read_reminders.py todos --list Personal --max 20
```

If a global `maccli` command is already available, these are equivalent:

```bash
maccli reminders doctor --probe
maccli reminders lists
```

## Command Surface

- Read: `doctor`, `lists`, `todos`, `todo`, `today`, `overdue`, `search`
- Write: `create`, `update`, `complete`, `uncomplete`, `move`, `delete`
- Output: JSON from `osascript`; parse it instead of scraping text.
- Permissions: Reminders access may require Automation or Reminders approval in System Settings > Privacy & Security.

## Workflow

1. Run `python3 scripts/read_reminders.py lists` to discover list names, IDs, and incomplete counts.
2. Use narrow reads: `today --max 20`, `overdue --max 20`, `todos --list <name> --max 20`, or `search <query> --max 20`.
3. Prefer list IDs and reminder IDs for writes. Names are acceptable for one-off reads.
4. Include body, due, flagged, or remind fields only when needed.
5. Treat timeouts and authorization errors as permission or performance issues, not empty data. Use `$macos-permissions` for TCC, Automation, or timeout troubleshooting.

## Write Safety

Write commands require `--confirm`. Do not add it until the user has approved the exact operation.

For `update`, `complete`, `uncomplete`, `move`, and `delete`, first read the target reminder and show:

- reminder title
- current list
- due/remind date when present
- reminder ID

`create` must specify `--list` or `--list-id`; do not assume a default list. `move` may return a new reminder ID in the destination list, so use the returned ID for any follow-up write. Confirm again before `delete`. For bulk changes, require an explicit reviewed target list and confirmation for that list.

## Examples

```bash
python3 scripts/read_reminders.py todo --reminder-id REMINDER_ID
python3 scripts/read_reminders.py create --list Personal --title "Buy milk" --due 2026-06-15 --confirm
python3 scripts/read_reminders.py update --reminder-id REMINDER_ID --title "Buy oat milk" --flagged --confirm
python3 scripts/read_reminders.py complete --reminder-id REMINDER_ID --confirm
python3 scripts/read_reminders.py move --reminder-id REMINDER_ID --to-list Work --confirm
python3 scripts/read_reminders.py delete --reminder-id REMINDER_ID --confirm
```
