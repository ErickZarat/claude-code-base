#!/usr/bin/env python3
"""
Checks that every fixed BLOCKER/MAJOR in a review ledger has a fix brief, so remediation fixes the cause, not the line.

A brief lives under `#### <ID>` in the ledger and needs these fields (one `- Field: …` line each):
  Fails when · Root cause · Same class elsewhere · Fix site · Tests (with "failed first: yes")
A finding seen 2+ times also needs `Previous fix missed:`. The latest row per ID decides its status.

Usage: fix_brief_check.py <ledger.md>     exit 0 = complete, 1 = gaps (listed)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FINDING_ROW = re.compile(r"^\|\s*(R\d+-(BLK|MAJ)-\d+)\s*\|")
BRIEF_HEADER = re.compile(r"^####\s+(R\d+-[A-Z]+-\d+)\s*$", re.MULTILINE)
FIXED_STATUSES = ("FIXED", "VERIFIED")
REQUIRED_FIELDS = ("Fails when", "Root cause", "Same class elsewhere", "Fix site", "Tests")
RECURRENCE_FIELD = "Previous fix missed"
FAILED_FIRST = re.compile(r"failed first:\s*yes", re.IGNORECASE)
STATUS_COLUMN, SEEN_COLUMN = 6, 5


def latest_major_rows(text: str) -> dict[str, list[str]]:
    """BLOCKER/MAJOR ID → cells of its last row in the ledger."""
    rows: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = FINDING_ROW.match(line)
        if match:
            rows[match.group(1)] = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return rows


def briefs(text: str) -> dict[str, str]:
    headers = list(BRIEF_HEADER.finditer(text))
    found = {}
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        found[header.group(1)] = text[header.end():end]
    return found


def field(brief: str, name: str) -> str:
    match = re.search(rf"^-\s*{re.escape(name)}:\s*(.+)$", brief, re.MULTILINE)
    return match.group(1).strip() if match else ""


def gaps_for(finding_id: str, cells: list[str], brief: str | None) -> list[str]:
    if brief is None:
        return [f"{finding_id}: no fix brief (add `#### {finding_id}` with {', '.join(REQUIRED_FIELDS)})"]
    gaps = [f"{finding_id}: missing '{name}'" for name in REQUIRED_FIELDS if not field(brief, name)]
    if field(brief, "Tests") and not FAILED_FIRST.search(field(brief, "Tests")):
        gaps.append(f"{finding_id}: no test shown failing before the fix")
    seen = cells[SEEN_COLUMN] if len(cells) > SEEN_COLUMN else "1"
    if seen.isdigit() and int(seen) >= 2 and not field(brief, RECURRENCE_FIELD):
        gaps.append(f"{finding_id}: seen {seen} times — missing '{RECURRENCE_FIELD}'")
    return gaps


def check(ledger_file: Path) -> tuple[int, list[str]]:
    text = ledger_file.read_text()
    found_briefs = briefs(text)
    fixed = {
        finding_id: cells for finding_id, cells in latest_major_rows(text).items()
        if len(cells) > STATUS_COLUMN and cells[STATUS_COLUMN].upper().startswith(FIXED_STATUSES)
    }
    gaps = [gap for finding_id, cells in fixed.items() for gap in gaps_for(finding_id, cells, found_briefs.get(finding_id))]
    return len(fixed), gaps


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    fixed_count, gaps = check(Path(sys.argv[1]))
    for gap in gaps:
        print(f"✗ {gap}")
    print(f"{fixed_count} BLOCKER/MAJOR fix(es) checked — {'complete' if not gaps else f'{len(gaps)} gap(s)'}")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
