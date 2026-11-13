#!/usr/bin/env python3
"""
Is this PR small enough to review well? Counts changed lines against the base branch, ignoring generated files.

Ignored: lockfiles, snapshot and golden files, build output (dist/, build/, out/, generated/).
Budget: --max, else $ENG_PR_MAX_LINES, else 600. Over budget → exit 1 with a per-folder breakdown to split by.

Usage: pr_size.py --base main [--max 600]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import Counter

DEFAULT_BUDGET = 600
IGNORED = re.compile(
    r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|[^/]*\.lock|[^/]*\.lockfile|go\.sum|Cargo\.lock)$"
    r"|(^|/)__snapshots__/|\.snap$|(^|/)golden/|\.golden(\.[a-z]+)?$"
    r"|(^|/)(dist|build|out|generated)/"
)


def changed_lines(base: str) -> Counter:
    """Changed lines per top-level folder, generated files excluded."""
    output = subprocess.run(["git", "diff", "--numstat", f"{base}...HEAD"], capture_output=True, text=True,
                            check=True).stdout
    per_folder: Counter = Counter()
    for line in output.splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-" or IGNORED.search(path):  # "-" = binary file
            continue
        folder = path.split("/", 1)[0] + "/" if "/" in path else path
        per_folder[folder] += int(added) + int(deleted)
    return per_folder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", required=True)
    parser.add_argument("--max", type=int, default=int(os.environ.get("ENG_PR_MAX_LINES", DEFAULT_BUDGET)))
    arguments = parser.parse_args()

    per_folder = changed_lines(arguments.base)
    total = sum(per_folder.values())
    if total <= arguments.max:
        print(f"PR size: {total} changed lines (budget {arguments.max}) — OK")
        return 0
    print(f"PR size: {total} changed lines > {arguments.max} — too big to review well. Split it, e.g. by folder:")
    for folder, lines in per_folder.most_common():
        print(f"  {folder:<40} {lines}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
