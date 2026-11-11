#!/usr/bin/env python3
"""
Builds the review packet: one markdown file with everything reviewers need, so each reviewer subagent
reads it once instead of re-running git commands and re-exploring the repository (the main token cost).

Contents: diff stats, changed files, requirement sources, triage (which specialist reviewers apply and a
suggested review depth), and the unified diff (truncated beyond a limit).

Usage:
  review_packet.py --base main --out .reviews/<branch>/packet.md [--since <commit>] [--max-diff-lines 3000]

  --since   only include changes after <commit> (used for re-review rounds: the remediation diff)
"""

from __future__ import annotations  # keeps type hints working on macOS's bundled Python 3.9

import argparse
import re
import subprocess
from pathlib import Path

DEFAULT_MAX_DIFF_LINES = 3000

PERFORMANCE_PATH_PATTERN = re.compile(r"(?i)(repositor|dao|query|queries|migration|\.sql$|cache|consumer|producer|client)")
PERFORMANCE_CODE_PATTERN = re.compile(
    r"(?i)\b(select|insert\s+into|update\s+\w+\s+set|delete\s+from|join|findAll|query|for\s*\(|forEach|while\s*\(|"
    r"\.map\s*[{(]|\.filter\s*[{(]|stream\(|http|fetch\(|kafka|redis|cache|thread|coroutine|launch\s*\{|async|await|sleep)\b"
)
SECURITY_PATH_PATTERN = re.compile(
    r"(?i)(auth|security|login|session|token|password|crypto|permission|controller|handler|route|endpoint|"
    r"config|settings|\.env|dockerfile|build\.gradle|pom\.xml|package\.json|requirements.*\.txt|pyproject\.toml|"
    r"go\.mod|\.tf$|helm|k8s|workflow)"
)
SECURITY_CODE_PATTERN = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|credential|authoriz|authent|permission|role|exec\(|eval\(|subprocess|"
    r"Runtime\.getRuntime|ProcessBuilder|innerHTML|dangerouslySetInnerHTML|deserializ|cors|csrf|verify\s*=\s*false|"
    r"trustAll|@PreAuthorize|@Secured|request\.(params|query|body))"
)
REQUIREMENT_PLAN_GLOB = "docs/plans/*.md"
SQL_STATEMENT = re.compile(
    r"(?i)\b(select\s.+\sfrom|insert\s+into|update\s+\w+\s+set|delete\s+from|\bwhere\s|order\s+by|group\s+by|values\s*\()"
)
# Values spliced into a string: Kotlin/JS/Groovy templates, concatenation, Python f-strings / % / format, printf-style.
STRING_SPLICING = re.compile(
    r"""\$\{|\$[A-Za-z_]|["']\s*\+|\+\s*["']|\bf["']|%\s*\(|%\s*[A-Za-z_]\w*\s*$|\.format\(|String\.format|sprintf|Sprintf"""
)
MAX_SQL_PREVIEW_LENGTH = 120
CONTRACT_FILE = re.compile(r"(?i)(\.proto$|\.graphqls?$|\.gql$|\.avsc$|(openapi|swagger)[^/]*\.(ya?ml|json)$)")
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
DEPTH_ORDER = ("quick", "standard", "thorough")
MINIMUM_DEPTH_LINE = re.compile(r"^\s*Minimum review depth:\s*(quick|standard|thorough)\b", re.IGNORECASE | re.MULTILINE)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def changed_files(diff_range: str) -> list[str]:
    return [line for line in git("diff", "--name-only", diff_range).splitlines() if line]


def added_lines(unified_diff: str) -> list[str]:
    return [line[1:] for line in unified_diff.splitlines() if line.startswith("+") and not line.startswith("+++")]


def added_lines_with_location(unified_diff: str) -> list[tuple[str, int, str]]:
    """(file, new line number, text) for every added line in a unified diff."""
    located, current_file, line_number = [], "", 0
    for line in unified_diff.splitlines():
        if line.startswith("+++ "):
            current_file = line[6:] if line.startswith("+++ b/") else line[4:]
        elif line.startswith("@@"):
            header = HUNK_HEADER.match(line)
            line_number = int(header.group(1)) if header else 0
        elif line.startswith("+"):
            located.append((current_file, line_number, line[1:]))
            line_number += 1
        elif not line.startswith("-") and not line.startswith("\\"):
            line_number += 1
    return located


def dynamic_sql_candidates(unified_diff: str) -> list[str]:
    """Added lines that build SQL by splicing values into strings — each one is a possible SQL injection."""
    return [
        f"- `{path}:{number}` — `{text.strip()[:MAX_SQL_PREVIEW_LENGTH]}`"
        for path, number, text in added_lines_with_location(unified_diff)
        if SQL_STATEMENT.search(text) and STRING_SPLICING.search(text)
    ]


def count_changed_lines(diff_range: str) -> int:
    total = 0
    for line in git("diff", "--numstat", diff_range).splitlines():
        added, deleted, _ = line.split("\t", 2)
        total += int(added) if added.isdigit() else 0
        total += int(deleted) if deleted.isdigit() else 0
    return total


def needs_review(paths: list[str], code_lines: list[str], path_pattern: re.Pattern, code_pattern: re.Pattern) -> bool:
    return any(path_pattern.search(path) for path in paths) or any(code_pattern.search(line) for line in code_lines)


def requirement_sources() -> list[str]:
    """Active OpenSpec change artifacts and plan files. Archived OpenSpec changes are history, not requirements."""
    sources = []
    changes_dir = Path("openspec/changes")
    if changes_dir.is_dir():
        for change_dir in sorted(path for path in changes_dir.iterdir() if path.is_dir() and path.name != "archive"):
            sources.extend(str(path) for path in sorted(change_dir.rglob("*.md")) if "reviews" not in path.parts)
    sources.extend(str(path) for path in sorted(Path(".").glob(REQUIREMENT_PLAN_GLOB)))
    return sources


DEFAULT_DEPTH = "standard"  # every dedicated reviewer runs; quick is only used when the user explicitly asks


def project_minimum_depth() -> str:
    """'Minimum review depth: <level>' from the project's CLAUDE.md; quick when absent."""
    claude_md = Path("CLAUDE.md")
    match = MINIMUM_DEPTH_LINE.search(claude_md.read_text()) if claude_md.is_file() else None
    return match.group(1).lower() if match else "quick"


def suggested_depth() -> tuple[str, str]:
    """The default depth, raised to the project minimum when that is deeper. Never lower than the default."""
    minimum = project_minimum_depth()
    if DEPTH_ORDER.index(minimum) > DEPTH_ORDER.index(DEFAULT_DEPTH):
        return minimum, "project minimum"
    return DEFAULT_DEPTH, "default — all dedicated reviewers"


def truncate(diff_text: str, max_lines: int) -> str:
    lines = diff_text.splitlines()
    if len(lines) <= max_lines:
        return diff_text
    omitted = len(lines) - max_lines
    return "\n".join(lines[:max_lines]) + f"\n... diff truncated: {omitted} more lines — open the files directly for the rest\n"


def build_packet(base: str, since: str | None, max_diff_lines: int) -> str:
    diff_range = f"{since}..HEAD" if since else f"{base}...HEAD"
    paths = changed_files(diff_range)
    unified_diff = git("diff", "--unified=5", diff_range)
    code_lines = added_lines(unified_diff)
    changed_line_count = count_changed_lines(diff_range)
    performance_needed = needs_review(paths, code_lines, PERFORMANCE_PATH_PATTERN, PERFORMANCE_CODE_PATTERN)
    security_needed = needs_review(paths, code_lines, SECURITY_PATH_PATTERN, SECURITY_CODE_PATTERN)
    sources = requirement_sources()

    sections = [
        "# Review packet",
        f"Range: `{diff_range}` · HEAD: `{git('rev-parse', '--short', 'HEAD').strip()}` · "
        f"{len(paths)} file(s), {changed_line_count} changed line(s)",
        "",
        "## Triage",
        "Suggested depth: {} — {}".format(*suggested_depth()),
        "Focus hints for reviewers (every reviewer still runs and checks everything):",
        f"- performance focus: {'yes' if performance_needed else 'no'}",
        f"- security focus: {'yes' if security_needed else 'no'}",
        "",
        "## Contract changes",
        "API contracts changed in this diff — check backwards compatibility, versioning and that the spec/PR documents",
        "the change (the `API contracts` CI check compares .proto and OpenAPI against the base branch).",
        *([f"- `{path}`" for path in paths if CONTRACT_FILE.search(path)] or ["- none"]),
        "",
        "## Dynamic SQL candidates",
        "Added lines that build SQL by splicing values into strings. Each must use bound parameters, or an allowlist",
        "for identifiers (ORDER BY / column / table names) — otherwise it is a SQL injection (BLK).",
        *(dynamic_sql_candidates(unified_diff) or ["- none found"]),
        "",
        "## Requirement sources",
        *(f"- {source}" for source in sources),
        *([] if sources else ["- none found in repo — use the PR description / linked issue"]),
        "",
        "## Changed files",
        "```",
        git("diff", "--stat=120", diff_range).rstrip(),
        "```",
        "",
        "## Diff",
        "```diff",
        truncate(unified_diff, max_diff_lines).rstrip(),
        "```",
        "",
    ]
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="main", help="base branch to compare against")
    parser.add_argument("--since", help="only changes after this commit (re-review rounds)")
    parser.add_argument("--out", required=True, help="where to write the packet markdown")
    parser.add_argument("--max-diff-lines", type=int, default=DEFAULT_MAX_DIFF_LINES)
    arguments = parser.parse_args()

    output_path = Path(arguments.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_packet(arguments.base, arguments.since, arguments.max_diff_lines))
    print(output_path)


if __name__ == "__main__":
    main()
