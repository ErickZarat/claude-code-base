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
FINDING_ROW = re.compile(r"^\|\s*R\d+-(?:(BLK|MAJ|MIN|S|Q)-)?\d+\s*\|")
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
            "code": match.group(1) or "?",
            "area": cells[2] if len(cells) > 2 else "?",
            "problem_class": re.sub(r"\s+", " ", problem_class).strip().lower(),
            "ledger": ledger_file,
        })
    return findings


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
