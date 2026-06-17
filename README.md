# mac-skills

Local-first macOS skills for AI coding agents.

`mac-skills` teaches agents how to work with macOS apps and local workflows through lightweight, auditable, permission-aware skills. The goal is not to collect random AppleScript snippets; the goal is to define reusable operation patterns that agents can follow safely.

## Available Skills

- `macos-calendar` - Read, create, update, and delete Apple Calendar events through a guarded `accli` wrapper.
- `macos-reminders` - Read, create, update, complete, move, and delete Apple Reminders through guarded `osascript` automation.
- `macos-notes` - Read and safely prepare Apple Notes changes through permission-aware local automation guidance.
- `macos-permissions` - Diagnose macOS app permission, TCC, Automation, and timeout issues.

## Install Skills

Install the stable `v0.1.0` release from GitHub:

```bash
npx skills add git@github.com:catwithtudou/mac-skills.git#v0.1.0
```

Use the HTTPS URL if SSH is not configured:

```bash
npx skills add https://github.com/catwithtudou/mac-skills.git#v0.1.0
```

The `v0.1.0` release includes `macos-calendar`, `macos-reminders`, `macos-notes`, `macos-permissions`, and the optional Calendar/Reminders `maccli` execution layer.

Install the development version from `main`:

```bash
npx skills add git@github.com:catwithtudou/mac-skills.git
```

Or use HTTPS for `main`:

```bash
npx skills add https://github.com/catwithtudou/mac-skills.git
```

Or install from a local checkout:

```bash
npx skills add ./
```

To inspect available skills without installing:

```bash
npx -y skills@latest add ./ --list
```

After installation, invoke the skills from an agent prompt, for example:

```text
Use $macos-calendar to check my calendar tomorrow.
Use $macos-reminders to create a reminder after confirming the details.
Use $macos-notes to search my Apple Notes for a project note.
Use $macos-permissions to troubleshoot a macOS permission or timeout issue.
```

For active development, a direct symlink into your agent's skill directory is also acceptable. The `skills` CLI is preferred for normal installation because it can install to supported agent directories consistently.

## Design Principles

1. Read operations should be easy.
2. Write operations should be explicit.
3. Destructive operations must require confirmation.
4. Prefer structured local APIs over fragile GUI automation.
5. Treat macOS permission failures as permission problems, not empty data.

## Optional CLI

This repository also ships `maccli`, a small Python execution layer used by the skills:

```bash
python3 -m pip install -e .
maccli --help
maccli calendar doctor
maccli reminders doctor --probe
```

Most users should install the skills first. Use `maccli` directly when developing this repository, debugging permissions, or manually verifying the local execution layer.

## Development Checks

Run these before publishing changes:

```bash
python3 -m compileall src scripts
PYTHONPATH=src python3 -m unittest discover -s tests
python3 scripts/validate_skills.py skills
PYTHONPATH=src python3 -m maccli --help
npx -y --registry=https://registry.npmjs.org skills@latest add ./ --list
```

## TODO

- Add optional scripts only when they make agent behavior safer, clearer, or more repeatable.
