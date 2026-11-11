#!/usr/bin/env python3
"""
Scenario ↔ test traceability for OpenSpec. Deterministic, no AI.

Every scenario has an ID: <capability>/<scenario-slug> (e.g. billing/refund-above-total-is-rejected).
A test claims a scenario with a marker comment anywhere in a test file:   // spec: billing/refund-above-total-is-rejected
(any comment style: //, #, --, /* */). Removed/renamed requirements need no tests.

Usage:
  trace.py [--change openspec/changes/<name>] [--fail-untested] [--list]
    no --change   → all main specs in openspec/specs
    --list        → print the scenario IDs to put in tests, grouped by requirement
    --fail-untested → exit 1 when any scenario has no test (use before /opsx:archive)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openspec_model import Requirement, change_spec_files, main_spec_files, parse_spec  # noqa: E402

MARKER = re.compile(r"\bspec:\s*([a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*)")
TEST_FILE = re.compile(
    r"""(?x)
    (?:^|/)(?:src/(?:test|testFixtures|integrationTest|it)|tests?|__tests__|spec|e2e)/ |
    (?:Test|Tests|IT|Spec)\.(?:kt|kts|java|scala|groovy)$ |
    [._-](?:test|spec)\.(?:ts|tsx|js|jsx|mjs|cjs|py|rb)$ |
    (?:^|/)test_[^/]*\.py$ | _test\.(?:go|py)$
    """
)
SKIPPED_DIRECTORIES = {".git", "node_modules", "build", "target", "dist", ".gradle", ".venv", "venv", "__pycache__",
                       "openspec", ".idea"}
TEXT_SUFFIXES = {".kt", ".kts", ".java", ".scala", ".groovy", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py",
                 ".go", ".rb", ".rs", ".cs", ".php", ".swift", ".sql", ".feature"}


def test_markers(root: Path) -> dict[str, list[str]]:
    """scenario ID → files that claim it."""
    markers: dict[str, list[str]] = {}
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = [name for name in subdirectories if name not in SKIPPED_DIRECTORIES]
        for file_name in files:
            path = Path(directory) / file_name
            relative = path.relative_to(root).as_posix()
            if path.suffix not in TEXT_SUFFIXES or not TEST_FILE.search(relative):
                continue
            for scenario_id in MARKER.findall(path.read_text(errors="ignore")):
                markers.setdefault(scenario_id, []).append(relative)
    return markers


def requirements_in_scope(change: str | None, root: Path) -> list[Requirement]:
    spec_files = change_spec_files(root / change) if change else main_spec_files(root / "openspec")
    return [requirement for spec_file in spec_files for requirement in parse_spec(spec_file) if requirement.needs_scenarios]


def all_known_ids(root: Path) -> set[str]:
    spec_files = main_spec_files(root / "openspec")
    changes = root / "openspec/changes"
    if changes.is_dir():
        for change_dir in changes.iterdir():
            if change_dir.is_dir() and change_dir.name != "archive":
                spec_files += change_spec_files(change_dir)
    return {scenario.scenario_id for spec_file in spec_files for r in parse_spec(spec_file) for scenario in r.scenarios}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--change")
    parser.add_argument("--fail-untested", action="store_true")
    parser.add_argument("--list", action="store_true")
    arguments = parser.parse_args()
    root = Path.cwd()

    requirements = requirements_in_scope(arguments.change, root)
    if arguments.list:
        for requirement in requirements:
            print(f"{requirement.name}")
            for scenario in requirement.scenarios:
                print(f"  spec: {scenario.scenario_id}")
        return 0

    markers = test_markers(root)
    tested, untested = [], []
    for requirement in requirements:
        for scenario in requirement.scenarios:
            (tested if scenario.scenario_id in markers else untested).append(scenario.scenario_id)
    stale = sorted(set(markers) - all_known_ids(root))

    print(f"Tested ({len(tested)}):")
    for scenario_id in tested:
        print(f"  ✓ {scenario_id}  ← {', '.join(markers[scenario_id])}")
    print(f"Untested ({len(untested)}):")
    for scenario_id in untested:
        print(f"  ✗ {scenario_id}")
    if stale:
        print(f"Stale markers ({len(stale)}) — scenario renamed or removed:")
        for scenario_id in stale:
            print(f"  ? {scenario_id}  ← {', '.join(markers[scenario_id])}")
    return 1 if arguments.fail_untested and untested else 0


if __name__ == "__main__":
    sys.exit(main())
