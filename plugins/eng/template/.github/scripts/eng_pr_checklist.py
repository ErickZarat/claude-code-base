#!/usr/bin/env python3
"""
PR checklist gate (installed by eng@claude-code-base).

A PR that is ready for review must:
  - link its issue with a closing keyword ("Closes #44") — unless the title starts with [NO-ISSUE];
  - use the same issue number in the title tag ([BUG-44], [TASK-44] …) as in the closing keyword;
  - have "## Acceptance criteria" (not required for [NO-ISSUE]) and "## Definition of Done" checklists;
  - have every item in Acceptance criteria, Definition of Done and Pending decisions checked.
Draft PRs only get a report, so work in progress is never blocked.

Input via environment variables (never interpolated into shell): PR_TITLE, PR_BODY, PR_DRAFT.
"""

from __future__ import annotations

import os
import re
import sys

CLOSING_KEYWORD = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+#(\d+)", re.IGNORECASE)
TITLE_TAG = re.compile(r"^\[[A-Z][A-Z0-9]*-(\d+)\]")  # [BUG-10], [TASK-44], [ISSUE-7] …
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HEADING = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
UNCHECKED_ITEM = re.compile(r"^\s*[-*]\s+\[ \]\s+(.+)$", re.MULTILINE)
ANY_ITEM = re.compile(r"^\s*[-*]\s+\[[ xX]\]\s+", re.MULTILINE)

ACCEPTANCE_CRITERIA = "acceptance criteria"
DEFINITION_OF_DONE = "definition of done"
PENDING_DECISIONS = "pending decisions"
CHECKED_SECTIONS = (ACCEPTANCE_CRITERIA, DEFINITION_OF_DONE, PENDING_DECISIONS)
DISPLAY_NAMES = {ACCEPTANCE_CRITERIA: "Acceptance criteria", DEFINITION_OF_DONE: "Definition of Done",
                 PENDING_DECISIONS: "Pending decisions"}


def split_sections(body: str) -> dict[str, str]:
    """Map lower-cased '## Heading' names to their text."""
    sections: dict[str, str] = {}
    headings = list(HEADING.finditer(body))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        sections[heading.group(1).strip().lower()] = body[heading.end():end]
    return sections


def find_problems(title: str, body: str) -> tuple[list[str], list[str]]:
    """Returns (structural problems, pending checklist items)."""
    body = HTML_COMMENT.sub("", body or "")
    sections = split_sections(body)
    is_ticketless = title.startswith("[NO-ISSUE]")
    problems: list[str] = []

    closed_issues = {int(number) for number in CLOSING_KEYWORD.findall(body)}
    if not is_ticketless and not closed_issues:
        problems.append("Link the issue in the PR body with a closing keyword, e.g. 'Closes #44'.")
    title_tag = TITLE_TAG.match(title)
    if title_tag and closed_issues and int(title_tag.group(1)) not in closed_issues:
        problems.append(f"The title tag refers to #{title_tag.group(1)} but the body closes "
                        f"{', '.join(f'#{n}' for n in sorted(closed_issues))} — they must match.")
    required_sections = [DEFINITION_OF_DONE] if is_ticketless else [ACCEPTANCE_CRITERIA, DEFINITION_OF_DONE]
    for section in required_sections:
        if section not in sections or not ANY_ITEM.search(sections[section]):
            problems.append(f"Add a '## {DISPLAY_NAMES[section]}' section with a checklist ('- [ ] ...').")

    pending = [
        f"{DISPLAY_NAMES[section]}: {item.strip()}"
        for section in CHECKED_SECTIONS if section in sections
        for item in UNCHECKED_ITEM.findall(sections[section])
    ]
    return problems, pending


def main() -> int:
    title = os.environ.get("PR_TITLE", "")
    is_draft = os.environ.get("PR_DRAFT", "false") == "true"
    problems, pending = find_problems(title, os.environ.get("PR_BODY", ""))

    for problem in problems:
        print(f"{'::warning::' if is_draft else '::error::'}{problem}")
    if pending:
        print(f"Pending ({len(pending)}):")
        for item in pending:
            print(f"  - [ ] {item}")
    if not problems and not pending:
        print("PR checklist complete.")
        return 0
    if is_draft:
        print("Draft PR: reported only. Mark it ready for review once everything above is checked.")
        return 0
    print("::error::This PR is not ready: check every item above (or move open questions to a follow-up issue).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
