"""
Minimal OpenSpec model shared by spec_lint.py and trace.py: requirements, scenarios and tasks parsed from Markdown.

Spec format (OpenSpec):  ## ADDED|MODIFIED|REMOVED|RENAMED Requirements · ### Requirement: <name> ·
#### Scenario: <name> followed by WHEN/THEN bullets. Capability = the folder holding spec.md.
Task format:  - [ ] 1.2 <title> (after: 1.1; size: S)   — the annotation is optional.
"""

from __future__ import annotations  # keeps type hints working on macOS's bundled Python 3.9

import re
from dataclasses import dataclass, field
from pathlib import Path

DELTA_SECTION = re.compile(r"^##\s+(ADDED|MODIFIED|REMOVED|RENAMED)\s+Requirements", re.IGNORECASE)
REQUIREMENT_HEADING = re.compile(r"^###\s+Requirement:\s*(.+?)\s*$")
SCENARIO_HEADING = re.compile(r"^####\s+Scenario:\s*(.+?)\s*$")
TASK_LINE = re.compile(r"^\s*- \[(?P<mark>[ xX])\] (?P<key>\d+(?:\.\d+)+)\s+(?P<rest>.*)$")
TASK_ANNOTATION = re.compile(r"\s*\((?P<body>[^()]*\b(?:after|size|req)\s*:[^()]*)\)\s*$", re.IGNORECASE)
ISSUE_TAG = re.compile(r"\[[A-Z][A-Z0-9]*-\d+\]\s*")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@dataclass
class Scenario:
    name: str
    capability: str
    file: Path
    line: int
    body: list[str] = field(default_factory=list)

    @property
    def scenario_id(self) -> str:
        """Stable ID used to link tests to this scenario: <capability>/<scenario-slug>."""
        return f"{self.capability}/{slugify(self.name)}"

    @property
    def has_when(self) -> bool:
        return any(re.search(r"\bWHEN\b", line) for line in self.body)

    @property
    def has_then(self) -> bool:
        return any(re.search(r"\bTHEN\b", line) for line in self.body)


@dataclass
class Requirement:
    name: str
    delta: str | None  # ADDED / MODIFIED / REMOVED / RENAMED, or None in main specs
    capability: str
    file: Path
    line: int
    scenarios: list[Scenario] = field(default_factory=list)

    @property
    def needs_scenarios(self) -> bool:
        return self.delta not in ("REMOVED", "RENAMED")


@dataclass
class Task:
    key: str
    title: str
    done: bool
    line: int
    after: list[str] = field(default_factory=list)
    size: str | None = None
    requirement_hint: str | None = None


def parse_spec(spec_file: Path) -> list[Requirement]:
    capability = spec_file.parent.name
    requirements: list[Requirement] = []
    delta: str | None = None
    current_scenario: Scenario | None = None
    for line_number, line in enumerate(spec_file.read_text().splitlines(), start=1):
        delta_match = DELTA_SECTION.match(line)
        if delta_match:
            delta, current_scenario = delta_match.group(1).upper(), None
            continue
        requirement_match = REQUIREMENT_HEADING.match(line)
        if requirement_match:
            requirements.append(Requirement(requirement_match.group(1), delta, capability, spec_file, line_number))
            current_scenario = None
            continue
        scenario_match = SCENARIO_HEADING.match(line)
        if scenario_match and requirements:
            current_scenario = Scenario(scenario_match.group(1), capability, spec_file, line_number)
            requirements[-1].scenarios.append(current_scenario)
            continue
        if line.startswith("#"):
            current_scenario = None
        elif current_scenario is not None:
            current_scenario.body.append(line)
    return requirements


def parse_tasks(tasks_file: Path) -> list[Task]:
    tasks = []
    for line_number, line in enumerate(tasks_file.read_text().splitlines(), start=1):
        match = TASK_LINE.match(line)
        if not match:
            continue
        rest = ISSUE_TAG.sub("", match.group("rest"))
        task = Task(match.group("key"), rest.strip(), match.group("mark").lower() == "x", line_number)
        annotation = TASK_ANNOTATION.search(rest)
        if annotation:
            task.title = rest[:annotation.start()].strip()
            for part in annotation.group("body").split(";"):
                name, _, value = part.partition(":")
                name, value = name.strip().lower(), value.strip()
                if name == "after":
                    task.after = [key.strip() for key in value.split(",") if key.strip()]
                elif name == "size":
                    task.size = value.upper()
                elif name == "req":
                    task.requirement_hint = value
        tasks.append(task)
    return tasks


def change_spec_files(change_dir: Path) -> list[Path]:
    return sorted((change_dir / "specs").glob("*/spec.md")) if (change_dir / "specs").is_dir() else []


def main_spec_files(openspec_dir: Path) -> list[Path]:
    return sorted((openspec_dir / "specs").glob("*/spec.md")) if (openspec_dir / "specs").is_dir() else []


def plan_levels(tasks: list[Task]) -> tuple[list[list[str]], list[str]]:
    """Open tasks grouped by dependency depth (level 1 = can start now) and the longest dependency chain.
    Done tasks count as satisfied; unknown keys and cycles are ignored here (spec_lint reports them)."""
    open_tasks = {task.key: task for task in tasks if not task.done}
    depth: dict[str, int] = {}
    longest_chain: dict[str, list[str]] = {}

    def resolve(key: str, visiting: frozenset) -> int:
        if key in depth:
            return depth[key]
        best_depth, best_chain = 1, [key]
        for dependency in open_tasks[key].after:
            if dependency in open_tasks and dependency not in visiting:
                dependency_depth = resolve(dependency, visiting | {key})
                if dependency_depth + 1 > best_depth:
                    best_depth, best_chain = dependency_depth + 1, longest_chain[dependency] + [key]
        depth[key], longest_chain[key] = best_depth, best_chain
        return best_depth

    for key in open_tasks:
        resolve(key, frozenset({key}))
    levels = [[key for key in open_tasks if depth[key] == level] for level in range(1, max(depth.values(), default=0) + 1)]
    critical = max(longest_chain.values(), key=len, default=[])
    return levels, critical
