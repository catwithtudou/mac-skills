---
name: macos-calendar
version: 0.3.1
description: Read and safely manage local Apple Calendar data on macOS using a bundled launcher backed by local maccli or pinned npm fallback. Use when an AI agent needs to inspect calendars, list events, read one event, check free/busy time, create events, update events, delete events, or troubleshoot Calendar permission access.
---

# macOS Calendar

## Quick Start

Use the bundled launcher for Apple Calendar work. It uses local `maccli` when available and falls back to `npx -y mac-skills@0.3.1`. Run commands from this skill directory. Run setup before the first real read in a fresh environment:

```bash
python3 scripts/read_calendar.py setup
python3 scripts/read_calendar.py calendars
python3 scripts/read_calendar.py events --calendar Work --from 2026-06-15 --to 2026-06-16 --max 20
```

If a global `maccli` command is already available, these are equivalent:

```bash
maccli calendar setup
maccli calendar calendars
```

## Command Surface

- Read: `doctor`, `setup`, `calendars`, `events`, `event`, `freebusy`, `config-show`
- Write: `create`, `update`, `delete`
- Dependency: `setup` installs `@joargp/accli` with npm when `accli` is missing.
- Output: prefer JSON output and parse it when possible.

## Workflow

1. Run `python3 scripts/read_calendar.py calendars` to discover calendar names and persistent IDs.
2. Query the smallest useful date range. Do not dump broad calendar history.
3. Prefer persistent calendar IDs when output provides them; names are acceptable for one-off reads.
4. Treat permission failures as permission problems, not as empty calendars. Use `$macos-permissions` for TCC, authorization, or timeout troubleshooting.
5. Report times with local timezone context when it affects the user's decision.

## Write Safety

Write commands require `--confirm`. Do not add it until the user has approved the exact operation.

For `update` and `delete`, first read the target event and show the user:

- calendar
- event title
- start/end time
- event ID

For `delete`, ask for confirmation again because it is destructive. For bulk changes, require an explicit reviewed target list and confirmation for that list.

## Examples

```bash
python3 scripts/read_calendar.py event --calendar Work --event-id EVENT_ID
python3 scripts/read_calendar.py freebusy --calendar Work --from 2026-06-15T09:00 --to 2026-06-15T18:00
python3 scripts/read_calendar.py create --calendar Work --summary "Project review" --start 2026-06-15T14:00 --end 2026-06-15T15:00 --confirm
python3 scripts/read_calendar.py update --calendar Work --event-id EVENT_ID --start 2026-06-15T15:00 --end 2026-06-15T16:00 --confirm
python3 scripts/read_calendar.py delete --calendar Work --event-id EVENT_ID --confirm
```
