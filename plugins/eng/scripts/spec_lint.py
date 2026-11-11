#!/usr/bin/env python3
"""
Spec lint: is an OpenSpec change ready to implement? Deterministic, no AI.

ERROR (blocks): requirement without scenarios · scenario without WHEN or THEN · no delta specs · no tasks.md ·
                task depending on an unknown task or in a dependency cycle.
WARN:           vague wording · no error/edge-case scenario · requirement no task seems to cover ·
                no "Non-functional requirements" section (proposal.md or design.md) · task sized L/XL.

Usage: spec_lint.py --change openspec/changes/<name> [--strict]     (--strict: warnings also fail)
Exit code: 0 ready · 1 not ready.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openspec_model import Requirement, Task, change_spec_files, parse_spec, parse_tasks  # noqa: E402

VAGUE_WORDS = re.compile(
    r"\b(quickly|fast|efficient(?:ly)?|properly|appropriate(?:ly)?|user-friendly|easy|easily|intuitive(?:ly)?|"
    r"seamless(?:ly)?|robust(?:ly)?|reasonable|as needed|if needed|etc\.?|and so on|various|tbd|todo|should handle)\b",
    re.IGNORECASE,
)
ERROR_CASE_WORDS = re.compile(
    r"(?i)\b(fail|fails|failure|reject|rejected|invalid|error|not found|unauthori[sz]ed|forbidden|denied|timeout|"
    r"times out|missing|empty|exceed|exceeds|conflict|duplicate|limit|[45]\d\d)\b"
)
NFR_HEADING = re.compile(r"(?im)^#+\s*non-functional")
STOP_WORDS = {"with", "from", "that", "this", "when", "then", "shall", "must", "should", "into", "for", "the", "and",
              "support", "allow", "system", "user", "users", "data", "able"}
LARGE_SIZES = {"L", "XL"}


class Report:
    def __init__(self, base: Path):
        self.base, self.errors, self.warnings = base, [], []

    def location(self, file: Path, line: int | None) -> str:
        try:
            shown = file.resolve().relative_to(self.base)
        except ValueError:
            shown = file
        return f"{shown}:{line}" if line else str(shown)

    def error(self, file: Path, line: int | None, message: str) -> None:
        self.errors.append(f"ERROR {self.location(file, line)} — {message}")

    def warn(self, file: Path, line: int | None, message: str) -> None:
        self.warnings.append(f"WARN  {self.location(file, line)} — {message}")


def significant_words(name: str) -> set[str]:
    return {word[:5] for word in re.findall(r"[a-z0-9]+", name.lower()) if len(word) >= 4 and word not in STOP_WORDS}


def check_specs(spec_files: list[Path], report: Report) -> list[Requirement]:
    requirements: list[Requirement] = []
    for spec_file in spec_files:
        requirements.extend(parse_spec(spec_file))
        for line_number, line in enumerate(spec_file.read_text().splitlines(), start=1):
            for match in VAGUE_WORDS.finditer(line):
                report.warn(spec_file, line_number, f"vague wording '{match.group(0)}' — state a measurable outcome")
    active = [requirement for requirement in requirements if requirement.needs_scenarios]
    for requirement in active:
        if not requirement.scenarios:
            report.error(requirement.file, requirement.line, f"requirement '{requirement.name}' has no scenarios")
        for scenario in requirement.scenarios:
            missing = [word for word, present in (("WHEN", scenario.has_when), ("THEN", scenario.has_then)) if not present]
            if missing:
                report.error(scenario.file, scenario.line, f"scenario '{scenario.name}' has no {' or '.join(missing)}")
    scenario_texts = [scenario.name + " " + " ".join(scenario.body) for r in active for scenario in r.scenarios]
    if scenario_texts and not any(ERROR_CASE_WORDS.search(text) for text in scenario_texts):
        report.warn(spec_files[0], None, "no error or edge-case scenario (invalid input, not found, limits, failures)")
    return active


def check_task_coverage(requirements: list[Requirement], tasks: list[Task], tasks_file: Path, report: Report) -> None:
    task_words = set()
    hinted = {task.requirement_hint.lower() for task in tasks if task.requirement_hint}
    for task in tasks:
        task_words |= significant_words(task.title)
    for requirement in requirements:
        if requirement.name.lower() in hinted:
            continue
        if not (significant_words(requirement.name) & task_words):
            report.warn(tasks_file, None, f"requirement '{requirement.name}' — no task seems to cover it "
                                          f"(add one, or annotate a task with '(req: {requirement.name})')")


def check_task_dependencies(tasks: list[Task], tasks_file: Path, report: Report) -> None:
    by_key = {task.key: task for task in tasks}
    for task in tasks:
        for dependency in task.after:
            if dependency not in by_key:
                report.error(tasks_file, task.line, f"task {task.key} depends on unknown task {dependency}")
        if task.size in LARGE_SIZES:
            report.warn(tasks_file, task.line, f"task {task.key} is size {task.size} — consider splitting it (one PR each)")

    visiting, finished = set(), set()

    def visit(key: str, path: list[str]) -> None:
        if key in finished or key not in by_key:
            return
        if key in visiting:
            report.error(tasks_file, by_key[key].line, f"dependency cycle: {' → '.join(path + [key])}")
            return
        visiting.add(key)
        for dependency in by_key[key].after:
            visit(dependency, path + [key])
        visiting.discard(key)
        finished.add(key)

    for key in by_key:
        visit(key, [])


def lint_change(change_dir: Path) -> Report:
    report = Report(Path.cwd().resolve())
    spec_files = change_spec_files(change_dir)
    if not spec_files:
        report.error(change_dir, None, "no delta specs (specs/<capability>/spec.md) — nothing to implement against")
    requirements = check_specs(spec_files, report) if spec_files else []

    tasks_file = change_dir / "tasks.md"
    if not tasks_file.is_file():
        report.error(tasks_file, None, "tasks.md is missing")
    else:
        tasks = parse_tasks(tasks_file)
        if not tasks:
            report.error(tasks_file, None, "tasks.md has no tasks ('- [ ] 1.1 …')")
        check_task_coverage(requirements, tasks, tasks_file, report)
        check_task_dependencies(tasks, tasks_file, report)

    planning_text = " ".join((change_dir / name).read_text() for name in ("proposal.md", "design.md")
                             if (change_dir / name).is_file())
    if not NFR_HEADING.search(planning_text):
        report.warn(change_dir / "design.md", None, "no 'Non-functional requirements' section in proposal.md or "
                                                    "design.md — state latency/volume/security/observability targets, or 'None'")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--change", required=True)
    parser.add_argument("--strict", action="store_true", help="warnings also fail")
    arguments = parser.parse_args()

    report = lint_change(Path(arguments.change))
    for line in report.errors + report.warnings:
        print(line)
    print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    failed = bool(report.errors) or (arguments.strict and bool(report.warnings))
    print("NOT READY" if failed else "READY")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
