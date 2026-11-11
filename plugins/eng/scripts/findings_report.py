#!/usr/bin/env python3
"""
Learning loop: aggregates review ledgers and shows which problems keep coming back, so they can become rules.

Reads every ledger.md under .reviews/ and openspec/changes/**/reviews/ (archived changes included).
A finding's problem class is the part of its fingerprint after " · " (e.g. "RefundRepo · N+1 query" → "n+1 query").
Superseded rows are skipped (their replacement is counted).

Usage: findings_report.py [--min 3]     (--min: occurrences needed to call a problem class recurring)
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

LEDGER_GLOBS = (".reviews/**/ledger.md", "openspec/changes/**/reviews/**/ledger.md")
FINDING_ROW = re.compile(r"^\|\s*R(\d+)-(?:(BLK|MAJ|MIN|S|Q)-)?\d+\s*\|")
ROUND_HEADER = re.compile(r"^##\s+Round\s+(\d+)\b(.*)$", re.MULTILINE)
CHANGED_LINES = re.compile(r"changed lines:\s*(\d+)", re.IGNORECASE)
MIN_LEDGERS_FOR_RECURRING = 2


def ledgers(root: Path) -> list[Path]:
    found = set()
    for pattern in LEDGER_GLOBS:
        found.update(root.glob(pattern))
    return sorted(found)


def parse_findings(ledger_file: Path) -> list[dict]:
    findings = []
    for line in ledger_file.read_text().splitlines():
        match = FINDING_ROW.match(line)
        if not match:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if any(cell.upper().startswith("SUPERSEDED") for cell in cells):
            continue
        fingerprint = cells[1] if len(cells) > 1 else ""
        problem_class = fingerprint.split("·", 1)[1] if "·" in fingerprint else ""
        findings.append({
            "round": int(match.group(1)),
            "code": match.group(2) or "?",
            "area": cells[2] if len(cells) > 2 else "?",
            "problem_class": re.sub(r"\s+", " ", problem_class).strip().lower(),
            "ledger": ledger_file,
        })
    return findings


def round_metrics(ledger_files: list[Path], findings: list[dict]) -> list[str]:
    """Is development getting it right the first time? Rounds per PR, first-round density, clean first rounds."""
    if not ledger_files:
        return []
    rounds, first_round_lines, counted_first_round_findings, clean_first_rounds = [], 0, 0, 0
    for ledger_file in ledger_files:
        text = ledger_file.read_text()
        headers = ROUND_HEADER.findall(text)
        ledger_findings = [finding for finding in findings if finding["ledger"] == ledger_file]
        rounds.append(max([int(number) for number, _ in headers] + [finding["round"] for finding in ledger_findings] + [1]))
        first_round = [finding for finding in ledger_findings if finding["round"] == 1]
        clean_first_rounds += not first_round
        first_header = next((rest for number, rest in headers if number == "1"), "")
        lines = CHANGED_LINES.search(first_header)
        if lines:
            first_round_lines += int(lines.group(1))
            counted_first_round_findings += len(first_round)
    density = (f"{counted_first_round_findings * 100 / first_round_lines:.1f}" if first_round_lines else "n/a")
    return [
        f"PRs reviewed: {len(ledger_files)} · average rounds per PR: {sum(rounds) / len(rounds):.1f} · "
        f"clean first round: {clean_first_rounds} of {len(ledger_files)}",
        f"first-round findings per 100 changed lines: {density}",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--min", type=int, default=3)
    arguments = parser.parse_args()
    root = Path.cwd()

    ledger_files = ledgers(root)
    findings = [finding for ledger_file in ledger_files for finding in parse_findings(ledger_file)]
    by_code = Counter(finding["code"] for finding in findings)
    by_area = Counter(finding["area"] for finding in findings)
    ledgers_by_class: dict[str, set[Path]] = defaultdict(set)
    count_by_class: Counter = Counter()
    for finding in findings:
        if finding["problem_class"]:
            count_by_class[finding["problem_class"]] += 1
            ledgers_by_class[finding["problem_class"]].add(finding["ledger"])

    print(f"Ledgers: {len(ledger_files)} · findings: {len(findings)}")
    for line in round_metrics(ledger_files, findings):
        print(line)
    print("By severity: " + ", ".join(f"{code} {count}" for code, count in by_code.most_common()))
    print("By area: " + ", ".join(f"{area} {count}" for area, count in by_area.most_common()))
    print(f"Recurring problem classes (≥ {arguments.min} findings in ≥ {MIN_LEDGERS_FOR_RECURRING} ledgers):")
    recurring = [(problem, count) for problem, count in count_by_class.most_common()
                 if count >= arguments.min and len(ledgers_by_class[problem]) >= MIN_LEDGERS_FOR_RECURRING]
    for problem, count in recurring:
        examples = ", ".join(sorted(str(path.relative_to(root).parent) for path in ledgers_by_class[problem])[:3])
        print(f"  - {problem}: {count} findings in {len(ledgers_by_class[problem])} ledgers (e.g. {examples})")
    if not recurring:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
