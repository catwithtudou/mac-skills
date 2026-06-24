---
name: macos-permissions
description: Diagnose and explain macOS local app permissions for agent workflows, including TCC, Automation, Calendar, Reminders, Notes, Accessibility, and Full Disk Access. Use when an AI agent sees permission errors, authorization prompts, timeouts, empty-looking results that may be permission failures, or needs to explain safe recovery steps for macOS app access.
---

# macOS Permissions

## Quick Start

Use this skill when a macOS app workflow fails, times out, or returns suspiciously empty data. Diagnose permissions before treating the result as real app state.

```bash
maccli calendar doctor
maccli reminders doctor --probe
maccli notes doctor --probe
```

This skill does not grant permissions or modify System Settings. It explains what to check and how to report the failure.

## Permission Areas

- Calendar: System Settings > Privacy & Security > Calendars
- Reminders: System Settings > Privacy & Security > Reminders
- Notes automation: System Settings > Privacy & Security > Automation
- GUI automation: System Settings > Privacy & Security > Accessibility
- File reads outside normal app APIs: System Settings > Privacy & Security > Full Disk Access

Only ask for the narrow permission needed for the current task. Do not request broad permissions as a default recovery step.

## Failure Triage

Classify the failure before answering:

1. Missing tool: the command or helper is not installed.
2. Permission denied: macOS blocks the app, terminal, or agent process.
3. Authorization prompt pending: the user may need to approve a macOS prompt.
4. Timeout: AppleScript, osascript, or the local app did not respond in time.
5. Real empty result: permissions and tools are healthy, but the app has no matching data.

Do not treat permission errors, denied prompts, or timeouts as empty data.

## Agent Workflow

1. Identify the target app and operation: read, write, destructive write, or GUI automation.
2. Run the narrowest safe doctor or read probe available.
3. Preserve the exact command, exit code, and short error text.
4. Explain the likely permission area and the System Settings path.
5. Ask the user to grant or confirm permission when needed, then retry only the same narrow probe.

For write operations, permission recovery does not replace user confirmation. Continue to require explicit confirmation for create, update, complete, move, or delete actions.

## Reporting Format

When reporting a permission issue, include:

- target app
- attempted operation
- observed failure
- likely permission area
- recovery path in System Settings
- next safe command to retry

Keep the report short and do not expose unrelated local app data.

## Safety Rules

- Do not use GUI automation to bypass macOS permission prompts.
- Do not claim data is absent when the probe timed out or lacked permission.
- Do not recommend Full Disk Access for Calendar, Reminders, or Notes API access unless a file-based workflow specifically requires it.
- Do not perform writes while diagnosing permissions.
