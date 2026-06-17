---
name: macos-notes
description: Read and safely manage local Apple Notes data on macOS through permission-aware local automation guidance. Use when Codex needs to inspect Notes accounts or folders, search or read notes, create a note after confirmation, prepare a safe update, delete a note with explicit confirmation, or troubleshoot Notes Automation permission access.
---

# macOS Notes

## Quick Start

Use this skill when the user wants to work with Apple Notes on macOS. There is no `maccli notes` command in this repository yet; prefer safe local automation only when the user has asked for a concrete Notes task.

Before treating a read as empty, check whether Notes or Automation permissions may have blocked access.

## Capability Boundary

- Read: list accounts or folders, search notes, read selected notes, summarize selected notes.
- Write: create notes, prepare targeted updates, move notes, or delete notes only after user confirmation.
- Fallbacks: prefer Shortcuts or AppleScript; use GUI automation only when the user explicitly accepts it and no better local interface is available.

Do not dump the full Notes library. Start with a narrow folder, account, title, or search query.

## Workflow

1. Identify the user's target: account, folder, title, query, or known note.
2. Run the narrowest read needed to find candidate notes.
3. If multiple notes match, show a short candidate list and ask the user to choose.
4. For read results, report only the fields needed for the task.
5. For permission errors, authorization prompts, timeouts, or suspicious empty results, use `$macos-permissions`.

## Write Safety

Never write to Notes until the user has approved the exact operation.

For create, show:

- target account or folder
- title
- body summary or exact body when short

For update, move, or delete, first read the target note and show:

- note title
- account and folder when available
- last modified date when available
- stable identifier when available

Ask again before delete because it is destructive. For bulk writes, require a reviewed target list and explicit confirmation for that list.

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
