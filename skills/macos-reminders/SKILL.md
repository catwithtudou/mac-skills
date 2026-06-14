---
name: macos-reminders
description: Read and safely manage local Apple Reminders data on macOS using maccli osascript automation. Use when Codex needs to inspect reminder lists, list todos, search reminders, create reminders, update reminders, complete or uncomplete reminders, move reminders between lists, delete reminders, or troubleshoot Reminders permission access.
---

# macOS Reminders

## Quick Start

Use `maccli reminders` for Apple Reminders work. Reads may be slow on large Reminders databases; run one Reminders command at a time.

```bash
maccli reminders doctor --probe
maccli reminders lists
maccli reminders todos --list Personal --max 20
```

If `maccli` is unavailable, use the bundled shim with the same subcommands:

```bash
python3 "$HOME/.codex/skills/macos-reminders/scripts/read_reminders.py" lists
```

## Command Surface

- Read: `doctor`, `lists`, `todos`, `todo`, `today`, `overdue`, `search`
- Write: `create`, `update`, `complete`, `uncomplete`, `move`, `delete`
- Output: JSON from `osascript`; parse it instead of scraping text.
- Permissions: Reminders access may require Automation or Reminders approval in System Settings > Privacy & Security.

## Workflow

1. Run `maccli reminders lists` to discover list names, IDs, and incomplete counts.
2. Use narrow reads: `today --max 20`, `overdue --max 20`, `todos --list <name> --max 20`, or `search <query> --max 20`.
3. Prefer list IDs and reminder IDs for writes. Names are acceptable for one-off reads.
4. Include body, due, flagged, or remind fields only when needed.
5. Treat timeouts and authorization errors as permission or performance issues, not empty data.

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
maccli reminders todo --reminder-id REMINDER_ID
maccli reminders create --list Personal --title "Buy milk" --due 2026-06-15 --confirm
maccli reminders update --reminder-id REMINDER_ID --title "Buy oat milk" --flagged --confirm
maccli reminders complete --reminder-id REMINDER_ID --confirm
maccli reminders move --reminder-id REMINDER_ID --to-list Work --confirm
maccli reminders delete --reminder-id REMINDER_ID --confirm
```
