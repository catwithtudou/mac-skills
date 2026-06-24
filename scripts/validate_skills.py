#!/usr/bin/env python3
"""Validate skill folders without relying on machine-local Codex files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


MAX_DESCRIPTION_LENGTH = 1024
MAX_SKILL_NAME_LENGTH = 64
MAX_SKILL_LINES = 100
ALLOWED_FRONTMATTER_KEYS = {"name", "version", "description", "license", "allowed-tools", "metadata"}
TEMPLATE_MARKERS = ("[TODO", "Structuring This Skill", "Not every skill requires")


def parse_flat_frontmatter(text: str) -> tuple[dict[str, str], str | None]:
    if not text.startswith("---\n"):
        return {}, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        return {}, "Invalid frontmatter format"

    values: dict[str, str] = {}
    for raw_line in match.group(1).splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith((" ", "\t")):
            return {}, "Nested frontmatter is not supported by this validator"
        key, separator, value = raw_line.partition(":")
        if not separator:
            return {}, f"Invalid frontmatter line: {raw_line}"
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key] = value
    return values, None


def parse_openai_yaml(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        match = re.match(r"^\s{2}([a-z_]+):\s*(.*)$", raw_line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key] = value
    return values


def validate_skill(skill_path: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return ["SKILL.md not found"]

    text = skill_md.read_text(encoding="utf-8")
    frontmatter, parse_error = parse_flat_frontmatter(text)
    if parse_error:
        errors.append(parse_error)
        return errors

    unexpected = set(frontmatter) - ALLOWED_FRONTMATTER_KEYS
    if unexpected:
        errors.append(f"Unexpected frontmatter key(s): {', '.join(sorted(unexpected))}")

    name = frontmatter.get("name", "").strip()
    version = frontmatter.get("version", "").strip()
    description = frontmatter.get("description", "").strip()
    if not name:
        errors.append("Missing required frontmatter key: name")
    if not description:
        errors.append("Missing required frontmatter key: description")

    if name:
        if name != skill_path.name:
            errors.append(f"Frontmatter name '{name}' does not match folder '{skill_path.name}'")
        if not re.fullmatch(r"[a-z0-9-]+", name):
            errors.append(f"Name '{name}' must be lowercase hyphen-case")
        if name.startswith("-") or name.endswith("-") or "--" in name:
            errors.append(f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens")
        if len(name) > MAX_SKILL_NAME_LENGTH:
            errors.append(f"Name is too long: {len(name)} > {MAX_SKILL_NAME_LENGTH}")

    if version and not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        errors.append(f"Version '{version}' must use semver, for example 1.2.3")

    if description:
        if "Use when" not in description:
            errors.append("Description must include trigger wording: 'Use when'")
        if "<" in description or ">" in description:
            errors.append("Description cannot contain angle brackets")
        if len(description) > MAX_DESCRIPTION_LENGTH:
            errors.append(f"Description is too long: {len(description)} > {MAX_DESCRIPTION_LENGTH}")

    line_count = len(text.splitlines())
    if line_count > MAX_SKILL_LINES:
        errors.append(f"SKILL.md is too long: {line_count} > {MAX_SKILL_LINES} lines")

    for marker in TEMPLATE_MARKERS:
        if marker in text:
            errors.append(f"Template marker remains in SKILL.md: {marker}")

    openai_yaml = skill_path / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        errors.append("agents/openai.yaml not found")
    else:
        metadata = parse_openai_yaml(openai_yaml.read_text(encoding="utf-8"))
        for key in ("display_name", "short_description", "default_prompt"):
            if not metadata.get(key):
                errors.append(f"agents/openai.yaml missing interface.{key}")
        if name and f"${name}" not in metadata.get("default_prompt", ""):
            errors.append(f"agents/openai.yaml default_prompt must mention ${name}")

    return errors


def iter_skill_dirs(root: Path) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Path not found: {root}")
    if (root / "SKILL.md").exists():
        return [root]
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "SKILL.md").exists())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate mac-skills skill folders.")
    parser.add_argument("path", type=Path, help="A skill directory or a directory containing skills")
    args = parser.parse_args(argv)

    try:
        skill_dirs = iter_skill_dirs(args.path)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 1
    if not skill_dirs:
        print(f"No skill folders found under {args.path}", file=sys.stderr)
        return 1

    failed = False
    for skill_dir in skill_dirs:
        errors = validate_skill(skill_dir)
        if errors:
            failed = True
            print(f"[FAIL] {skill_dir}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[OK] {skill_dir}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
