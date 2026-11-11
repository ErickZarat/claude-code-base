#!/usr/bin/env python3
"""
Lightweight decision records (ADRs) in docs/decisions/NNNN-<slug>.md — the durable "why" that outlives an
OpenSpec change's design.md (which is archived with the change).

Usage:
  decisions.py new --title "Use keyset pagination" [--change add-refunds] [--supersedes 3]   → prints the new path
  decisions.py list
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

DECISIONS_DIR = Path("docs/decisions")
RECORD_FILE = re.compile(r"^(\d{4})-.+\.md$")
STATUS_LINE = re.compile(r"^Status: .*$", re.MULTILINE)
TITLE_LINE = re.compile(r"^# \d{4}\. (.+)$", re.MULTILINE)

TEMPLATE = """# {number:04d}. {title}

Status: Proposed
Date: {date}
{links}
## Context
<!-- The forces at play: requirement, constraint or problem that forces a choice. -->

## Options considered
<!-- 2–4 real options, one line each with its main trade-off. -->

## Decision
<!-- What we chose, in one or two sentences. -->

## Consequences
<!-- What becomes easier or harder; follow-ups; what would make us revisit this. -->
"""


def existing_records() -> list[Path]:
    if not DECISIONS_DIR.is_dir():
        return []
    return sorted(path for path in DECISIONS_DIR.iterdir() if RECORD_FILE.match(path.name))


def record_path(number: int) -> Path:
    match = next((path for path in existing_records() if path.name.startswith(f"{number:04d}-")), None)
    if match is None:
        raise SystemExit(f"error: decision {number:04d} not found in {DECISIONS_DIR}")
    return match


def create(title: str, change: str | None, supersedes: int | None) -> Path:
    numbers = [int(RECORD_FILE.match(path.name).group(1)) for path in existing_records()]
    number = max(numbers, default=0) + 1
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    links = []
    if change:
        links.append(f"OpenSpec change: openspec/changes/{change}")
    if supersedes:
        links.append(f"Supersedes: [{supersedes:04d}]({record_path(supersedes).name})")
    path = DECISIONS_DIR / f"{number:04d}-{slug}.md"
    DECISIONS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(number=number, title=title, date=datetime.date.today().isoformat(),
                                    links="".join(f"{link}\n" for link in links)))
    if supersedes:
        old = record_path(supersedes)
        old.write_text(STATUS_LINE.sub(f"Status: Superseded by [{number:04d}]({path.name})", old.read_text(), count=1))
    return path


def list_records() -> None:
    for path in existing_records():
        text = path.read_text()
        status = STATUS_LINE.search(text)
        title = TITLE_LINE.search(text)
        status_text = re.sub(r"\]\([^)]*\)", "]", status.group(0)[len("Status: "):]) if status else "?"
        print(f"{path.name[:4]}  {status_text:<24}  {title.group(1) if title else path.stem}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    new_parser = commands.add_parser("new")
    new_parser.add_argument("--title", required=True)
    new_parser.add_argument("--change")
    new_parser.add_argument("--supersedes", type=int)
    commands.add_parser("list")
    arguments = parser.parse_args()
    if arguments.command == "new":
        print(create(arguments.title, arguments.change, arguments.supersedes).as_posix())
    else:
        list_records()
    return 0


if __name__ == "__main__":
    sys.exit(main())
