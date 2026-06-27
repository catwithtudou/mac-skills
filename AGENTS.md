# Repository Guidelines

## Project Structure & Module Organization

This repository is a lightweight macOS skill collection for AI agents.

- `README.md` explains the project scope, install path, and roadmap.
- `.github/workflows/ci.yml` runs cross-platform validation on push and pull request.
- `package.json` defines the npm-distributed `maccli` and `mac-skills` command entrypoints.
- `bin/maccli.js` launches the Python `maccli` module from npm installs.
- `src/maccli/` contains the shared Python CLI execution layer.
- `scripts/validate_skills.py` validates skill folder structure for local checks and CI.
- `skills/macos-calendar/` contains the Apple Calendar skill.
- `skills/macos-reminders/` contains the Apple Reminders skill.
- `skills/macos-notes/` contains the Apple Notes skill.
- `skills/macos-permissions/` contains the macOS permissions troubleshooting skill.
- `skills/<name>/SKILL.md` is the required entrypoint for each skill.
- `skills/<name>/scripts/` holds optional executable helpers.
- `skills/<name>/agents/openai.yaml` stores UI-facing skill metadata when present.

Add one directory per skill using lowercase hyphenated names, for example `skills/macos-reminders/`.

## Build, Test, and Development Commands

Use these checks before submitting changes:

- `git status --short` shows the files changed in the working tree.
- `git diff -- README.md AGENTS.md package.json pyproject.toml bin/ src/ skills/` reviews CLI, skill, and documentation edits.
- `git log --oneline -n 5` checks recent commit style.
- `npm ci` installs the npm package lock for validation.
- `python3 -m pip install -e .` installs the local `maccli` console command for development.
- `python3 -m compileall src scripts skills` checks Python syntax.
- `python3 scripts/validate_skills.py skills` validates all skill folders.
- `node bin/maccli.js --help` verifies the npm CLI wrapper.
- `maccli --help` verifies the installed CLI entrypoint when available.
- `maccli calendar doctor` checks local macOS Calendar tooling.
- `maccli reminders doctor --probe` checks local Reminders access.
- `npm pack --dry-run` verifies the npm package contents.
- `npx -y skills@latest add ./ --list` verifies that the skills CLI can discover packaged skills.

When adding executable code, include the exact setup, build, lint, and test commands in `README.md` in the same change.

## Coding Style & Naming Conventions

Keep Markdown concise and scannable. Use sentence-case headings, short paragraphs, and fenced code blocks for commands. Prefer ASCII unless a file already uses another character set or the content requires it.

For scripts and modules, use descriptive lowercase names with underscores or hyphens consistently with the local language, such as `calendar.py` or `read_calendar.py`. Keep skill directory names lowercase and hyphenated. Do not introduce generated files, local caches, personal data, or machine-specific absolute paths.

## Testing Guidelines

There is no automated coverage target yet. For documentation changes, verify Markdown renders cleanly and that paths and commands match the repository. For skills, run `quick_validate.py` and at least one safe local command such as `doctor`. Name future tests after the behavior being verified, for example `test_window_focus.py`.

## Commit & Pull Request Guidelines

The current history contains only `first commit`, so no formal convention is established. Use concise, imperative commit subjects going forward, such as `Add window focus skill` or `Document setup commands`.

Pull requests should include a short summary, the reason for the change, verification performed, and any known limitations. Link related issues when available. Include screenshots or terminal output only when they clarify behavior or verification.

## Agent-Specific Instructions

Start from the real repository state before making changes. Prefer minimal, safe edits that preserve existing structure. Public skills must be generic: remove personal calendars, local usernames, private paths, and organization-specific assumptions before publishing.
