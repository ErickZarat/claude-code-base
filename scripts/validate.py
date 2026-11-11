#!/usr/bin/env python3
"""Static checks for the marketplace and plugin: JSON validity, manifest consistency, skill/agent frontmatter.

Run: python3 scripts/validate.py   (exit code 1 on any problem)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
KEBAB_CASE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
ALLOWED_AGENT_MODELS = {"haiku", "sonnet", "opus", "inherit"}
MAX_SKILL_DESCRIPTION_LENGTH = 200  # descriptions are sent on every request

problems: list[str] = []


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        problems.append(f"{path.relative_to(REPO_ROOT)}: invalid JSON ({error})")
        return {}


def frontmatter_fields(markdown_file: Path) -> dict[str, str]:
    match = FRONTMATTER.match(markdown_file.read_text())
    if not match:
        problems.append(f"{markdown_file.relative_to(REPO_ROOT)}: missing YAML frontmatter")
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if separator and not line.startswith((" ", "-")):
            fields[key.strip()] = value.strip()
    return fields


def check_named_markdown(markdown_file: Path, expected_name: str, kind: str) -> None:
    fields = frontmatter_fields(markdown_file)
    relative = markdown_file.relative_to(REPO_ROOT)
    if fields.get("name") != expected_name:
        problems.append(f"{relative}: {kind} name '{fields.get('name')}' must equal '{expected_name}'")
    if not KEBAB_CASE.match(expected_name):
        problems.append(f"{relative}: {kind} name must be kebab-case")
    if len(fields.get("description", "")) < 20:
        problems.append(f"{relative}: {kind} needs a meaningful description (it decides when Claude uses it)")


def check_plugin(plugin_dir: Path) -> None:
    manifest = load_json(plugin_dir / ".claude-plugin/plugin.json")
    if not SEMVER.match(manifest.get("version", "")):
        problems.append(f"{plugin_dir.name}: plugin.json version must be semver")

    hooks_config = load_json(plugin_dir / "hooks/hooks.json")
    for hook_groups in hooks_config.get("hooks", {}).values():
        for group in hook_groups:
            for hook in group.get("hooks", []):
                script = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"\s]+)", hook.get("command", ""))
                if script and not (plugin_dir / script.group(1)).is_file():
                    problems.append(f"{plugin_dir.name}: hook script {script.group(1)} not found")

    for skill_file in sorted(plugin_dir.glob("skills/*/SKILL.md")):
        check_named_markdown(skill_file, skill_file.parent.name, "skill")
        description_length = len(frontmatter_fields(skill_file).get("description", ""))
        if description_length > MAX_SKILL_DESCRIPTION_LENGTH:
            problems.append(f"{skill_file.relative_to(REPO_ROOT)}: description is {description_length} chars; "
                            f"keep it under {MAX_SKILL_DESCRIPTION_LENGTH} (costs tokens on every request)")
    for agent_file in sorted(plugin_dir.glob("agents/*.md")):
        check_named_markdown(agent_file, agent_file.stem, "agent")
        model = frontmatter_fields(agent_file).get("model", "inherit")
        if model not in ALLOWED_AGENT_MODELS:
            problems.append(f"{agent_file.relative_to(REPO_ROOT)}: model '{model}' not in {sorted(ALLOWED_AGENT_MODELS)}")
        if model in {"opus", "inherit"}:
            problems.append(f"{agent_file.relative_to(REPO_ROOT)}: pin a cheaper default model (sonnet/haiku); "
                            "escalate to opus per call for thorough reviews")

    template_settings = plugin_dir / "template/.claude/settings.json"
    if template_settings.exists():
        load_json(template_settings)

    for rule_file in sorted(plugin_dir.glob("template/.claude/rules/**/*.md")):
        if "paths:" in rule_file.read_text()[:200]:
            frontmatter_fields(rule_file)


def main() -> int:
    marketplace = load_json(REPO_ROOT / ".claude-plugin/marketplace.json")
    for required in ("name", "owner", "plugins"):
        if required not in marketplace:
            problems.append(f"marketplace.json: missing '{required}'")

    for entry in marketplace.get("plugins", []):
        plugin_dir = (REPO_ROOT / entry.get("source", "")).resolve()
        if not (plugin_dir / ".claude-plugin/plugin.json").is_file():
            problems.append(f"marketplace.json: plugin '{entry.get('name')}' source has no .claude-plugin/plugin.json")
            continue
        plugin_name = load_json(plugin_dir / ".claude-plugin/plugin.json").get("name")
        if plugin_name != entry.get("name"):
            problems.append(f"marketplace.json: entry '{entry.get('name')}' does not match plugin.json name '{plugin_name}'")
        check_plugin(plugin_dir)

    for problem in problems:
        print(f"✗ {problem}")
    print("✓ all checks passed" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
