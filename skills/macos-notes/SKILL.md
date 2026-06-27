---
name: macos-notes
version: 0.3.1
description: Read and safely manage local Apple Notes data on macOS using a bundled launcher backed by local maccli or pinned npm fallback. Use when an AI agent needs to inspect Notes accounts or folders, search or read notes, create a note after confirmation, guarded-delete a note with explicit double confirmation, or troubleshoot Notes Automation permission access.
---

# macOS Notes

## Quick Start

Use this skill when the user wants to work with Apple Notes on macOS. Prefer the bundled launcher because it keeps reads narrow, requires confirmation before writes, uses local `maccli` when available, and falls back to `npx -y mac-skills@0.3.1`. Run commands from this skill directory:

```bash
python3 scripts/read_notes.py doctor --probe
python3 scripts/read_notes.py accounts
python3 scripts/read_notes.py folders --account "iCloud"
python3 scripts/read_notes.py search "project"
python3 scripts/read_notes.py note --note-id "NOTE_ID"
```

Before treating a read as empty, check whether Notes or Automation permissions may have blocked access.

## Capability Boundary

- Read: list accounts or folders, list notes in an explicit folder, search notes, read a selected note.
- Write: create notes after `--confirm`; delete notes only after `--confirm --confirm-delete`.
- Deferred: update and move are not default capabilities because Notes bodies are HTML-like content and move behavior needs write verification.
- Fallbacks: prefer `python3 scripts/read_notes.py`, then Shortcuts or AppleScript. Use GUI automation only when the user explicitly accepts it and no better local interface is available.

Do not dump the full Notes library. Start with a narrow folder, account, title, or search query.

## Workflow

1. Identify the user's target: account, folder, title, query, or known note.
2. Run the narrowest read needed to find candidate notes:

   ```bash
   python3 scripts/read_notes.py search "launch" --max 10
   python3 scripts/read_notes.py notes --account "iCloud" --folder "Notes" --max 10
   ```

3. If multiple notes match, show a short candidate list and ask the user to choose.
4. For read results, report only the fields needed for the task.
5. For permission errors, authorization prompts, timeouts, or suspicious empty results, use `$macos-permissions`.

## Write Safety

Never write to Notes until the user has approved the exact operation.

For create, show:

- target account or folder
- title
- body summary or exact body when short

Create only after confirmation:

```bash
python3 scripts/read_notes.py create --account "iCloud" --folder "Notes" --title "Draft" --body "..." --confirm
```

For delete, first read the target note and show:

- note title
- account and folder when available
- last modified date when available
- stable identifier when available

Ask again before delete because it is destructive, then use both confirmation flags:

```bash
python3 scripts/read_notes.py delete --note-id "NOTE_ID" --confirm --confirm-delete
```

For bulk writes, require a reviewed target list and explicit confirmation for that list.

## Reporting Format

When reporting Notes results, keep the output compact:

```json
{
  "operation": "search_notes",
  "source": "Apple Notes",
  "status": "success",
  "items": [],
  "requires_confirmation": false,
  "next_action": null
}
```

## Safety Rules

- Do not assume the default Notes account or folder.
- Do not treat permission failures as empty search results.
- Do not expose unrelated note titles or bodies.
- Do not modify note bodies silently; preserve existing content unless the user confirms replacement.
- Do not delete notes without explicit, second confirmation.
