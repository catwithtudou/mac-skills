# mac-skills

![mac-skills cover](https://raw.githubusercontent.com/catwithtudou/mac-skills/main/assets/mac-skills-cover.png)

Local-first macOS skills for AI coding agents.

`mac-skills` helps AI agents work with macOS apps and local workflows through lightweight, auditable, permission-aware skills.

This project is **not** a random collection of AppleScript snippets.
It defines reusable macOS operation patterns that agents can follow safely across tools such as Claude Code, Cursor, Codex, Gemini CLI, and other local-first AI coding agents.

## Why mac-skills?

AI agents are increasingly expected to interact with local apps, files, reminders, calendars, notes, and personal workflows. On macOS, these operations are often fragile because of permissions, AppleScript behavior, app state, and destructive actions.

`mac-skills` provides a safer layer by teaching agents:

- when read-only access is acceptable;
- when user confirmation is required;
- how to handle macOS permission and TCC failures;
- which local execution path to prefer;
- how to avoid treating permission errors as empty data;
- how to use structured, repeatable workflows instead of ad-hoc GUI automation.

## Available Skills

| Skill | What it does | Execution layer | Safety model |
|---|---|---|---|
| `macos-calendar` | Read, create, update, and delete Apple Calendar events | Bundled launcher backed by local `maccli` or pinned npm fallback | Confirms writes and destructive actions |
| `macos-reminders` | Read, create, update, complete, move, and delete Apple Reminders | Bundled launcher backed by local `maccli` or pinned npm fallback | Confirms completion, move, delete, and bulk changes |
| `macos-notes` | Read, search, create, and guarded-delete Apple Notes | Bundled launcher backed by local `maccli` or pinned npm fallback | Treats note deletion and broad access as high-risk |
| `macos-permissions` | Diagnose macOS permissions, TCC, Automation, and timeout issues | Local diagnostic guidance and probes | Prevents silent permission-related false results |

## Requirements

- macOS.
- Apple Calendar, Reminders, and Notes installed locally.
- Node.js / `npx` for installing skills and using the npm CLI fallback.
- Python 3 for the local execution layer.
- macOS permissions for Calendar, Reminders, Notes, and Automation when required.

Some operations may trigger macOS permission prompts. If access fails, use `$macos-permissions` or the relevant `maccli ... doctor` command to diagnose the issue.

## Quick Start

Install the latest version from the repository default branch:

```bash
npx -y skills@latest add catwithtudou/mac-skills
```

Or use the full GitHub URL:

```bash
npx -y skills@latest add https://github.com/catwithtudou/mac-skills
```

After installation, invoke the skills from your agent prompt:

```text
Use $macos-calendar to check my calendar tomorrow.
Use $macos-reminders to create a reminder after confirming the details.
Use $macos-notes to search my Apple Notes for a project note.
Use $macos-permissions to troubleshoot a macOS permission or timeout issue.
```

To inspect available skills without installing:

```bash
npx -y skills@latest add catwithtudou/mac-skills --list
```

## Other Install Options

Install with SSH:

```bash
npx -y skills@latest add git@github.com:catwithtudou/mac-skills.git
```

Install from a local checkout:

```bash
git clone https://github.com/catwithtudou/mac-skills.git
cd mac-skills
npx -y skills@latest add ./
```

For active development, a direct symlink into your agent's skill directory is also acceptable. The `skills` CLI is preferred for normal installation because it can install to supported agent directories consistently.

## Reproducible Install

For reproducible installation, pin a release tag:

```bash
npx -y skills@latest add https://github.com/catwithtudou/mac-skills.git#v0.3.1
```

Use this when you want a stable, repeatable setup instead of tracking the repository default branch.

## Update

Update installed skills:

```bash
npx -y skills@latest update
```

## Optional CLI: maccli

This repository ships `maccli`, a small local execution layer used by the skills.

Installed skills include launchers under each skill's `scripts/` directory. They use a local `maccli` command when available and fall back to `npx -y mac-skills@0.3.1`, so users do not need to configure Python package entrypoints by hand.

Run without installing:

```bash
npx -y mac-skills reminders doctor --probe
npx -y mac-skills calendar calendars
npx -y mac-skills notes search "project"
```

Install globally:

```bash
npm install -g mac-skills
maccli reminders lists
```

For local repository development:

```bash
node bin/maccli.js --help
PYTHONPATH=src python3 -m maccli --help
```

Set `MACCLI_PYTHON=/path/to/python3` when the npm wrapper should use a specific Python interpreter.

The current repository version includes:

- `macos-calendar`
- `macos-reminders`
- `macos-notes`
- `macos-permissions`
- npm-distributed Calendar / Reminders / Notes execution support through `maccli`

## Safety Principles

1. Read operations should be easy.
2. Write operations should be explicit.
3. Destructive operations must require confirmation.
4. Bulk changes must require confirmation.
5. Prefer structured local APIs over fragile GUI automation.
6. Treat macOS permission failures as permission problems, not empty data.
7. Return structured results whenever possible.
8. Never silently delete, send, move, or overwrite local user data.

## Privacy Notes

`mac-skills` is designed as a local-first skill collection. The local execution layer runs on your machine and does not intentionally upload macOS app data by itself.

However, the AI agent or model provider you use may receive the context you choose to share in prompts, tool results, or conversations. Review your agent's privacy and data handling settings before using these skills with sensitive local data.

## Development Checks

Run these before publishing changes:

```bash
npm ci
python3 -m compileall src scripts skills
PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/validate_skills.py skills
PYTHONPATH=src python3 -m maccli --help
node bin/maccli.js --help
npm pack --dry-run
npx -y --registry=https://registry.npmjs.org skills@latest add ./ --list
```

## Roadmap

- Add optional scripts only when they make agent behavior safer, clearer, or more repeatable.
- Improve structured JSON output contracts for local operations.
- Add more permission diagnostics for common macOS TCC and Automation failures.
- Explore optional EventKit-backed execution for Calendar and Reminders.
- Add compatibility notes for more agent runtimes.
