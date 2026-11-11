#!/usr/bin/env python3
"""
Syncs an OpenSpec change to GitHub: one epic issue per change, one task issue per open task in tasks.md,
linked to the epic as sub-issues. Tags every task in tasks.md with [ISSUE-<n>] and records the mapping in
<change>/github.json so re-running only creates what is new.

GitHub is reached through the GitHubClient port; GhCliClient is the adapter that uses the `gh` CLI.

Usage:
  github_sync.py sync   --change openspec/changes/<name> [--group-by task|section] [--dry-run] [--repo owner/name]
  github_sync.py next   --change openspec/changes/<name>       # prints the next issue number to work on
  github_sync.py branch --issue 43 --title "POST /refunds endpoint"
  github_sync.py title  --issue 43 --type feat --title "POST /refunds endpoint"
"""

from __future__ import annotations  # keeps type hints working on macOS's bundled Python 3.9

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

TAG_PREFIX = "ISSUE"
MAPPING_FILE_NAME = "github.json"
MAX_BRANCH_LENGTH = 60
MAX_PROPOSAL_EXCERPT_LINES = 40

TASK_LINE = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>[ xX])\] (?P<key>\d+(?:\.\d+)+)\s+(?P<rest>.*)$")
SECTION_LINE = re.compile(r"^## (?P<key>\d+)\.\s+(?P<rest>.*)$")
EXISTING_TAG = re.compile(rf"\[{TAG_PREFIX}-(\d+)\]\s*")

LABELS = {
    "epic": ("5319e7", "OpenSpec change tracked as an epic"),
    "task": ("0e8a16", "Task from an OpenSpec change"),
}


# --- Domain ----------------------------------------------------------------------------------

class SyncError(Exception):
    """The change cannot be synced (missing files, unreadable mapping)."""


@dataclass(frozen=True)
class CreatedIssue:
    number: int
    issue_id: int  # GitHub's internal id — required to link sub-issues (not the visible number)


@dataclass
class WorkItem:
    """A unit that becomes one GitHub issue: a single task, or a whole section when grouping by section."""
    key: str
    title: str
    done: bool
    line_index: int
    issue_number: int | None = None
    subtasks: list[str] = field(default_factory=list)


@dataclass
class SyncReport:
    epic_number: int | None = None
    created_issue_numbers: list[int] = field(default_factory=list)
    planned_titles: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def item_label(item: WorkItem) -> str:
    """'1.1 Title' for tasks, '1. Title' for sections — matching how they read in tasks.md."""
    separator = "" if "." in item.key else "."
    return f"{item.key}{separator} {item.title}"


def issue_tag(issue_number: int) -> str:
    return f"[{TAG_PREFIX}-{issue_number}]"


def branch_name(issue_number: int, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    prefix = f"issue-{issue_number}-"
    return (prefix + slug)[:MAX_BRANCH_LENGTH].rstrip("-")


def pr_title(issue_number: int, change_type: str, title: str) -> str:
    return f"{issue_tag(issue_number)} {change_type}: {title}"


# --- Port and adapter --------------------------------------------------------------------------

class GitHubClient(Protocol):
    def create_issue(self, title: str, body: str, labels: list[str]) -> CreatedIssue: ...
    def update_issue_body(self, number: int, body: str) -> None: ...
    def add_sub_issue(self, parent_number: int, child_issue_id: int) -> bool: ...
    def ensure_label(self, name: str, color: str, description: str) -> None: ...
    def ensure_autolink(self, key_prefix: str, url_template: str) -> bool: ...
    def open_pull_request_titles(self) -> list[str]: ...
    def is_issue_open(self, number: int) -> bool: ...


def run_command(command: list[str]) -> str:
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


class GhCliClient:
    """GitHubClient adapter backed by the `gh` CLI (uses the user's existing gh authentication)."""

    def __init__(self, repo: str, run: Callable[[list[str]], str] = run_command):
        self.repo = repo
        self.run = run

    def create_issue(self, title: str, body: str, labels: list[str]) -> CreatedIssue:
        command = ["gh", "api", f"repos/{self.repo}/issues", "-f", f"title={title}", "-f", f"body={body}"]
        for label in labels:
            command += ["-f", f"labels[]={label}"]
        created = json.loads(self.run(command))
        return CreatedIssue(number=created["number"], issue_id=created["id"])

    def update_issue_body(self, number: int, body: str) -> None:
        self.run(["gh", "api", "-X", "PATCH", f"repos/{self.repo}/issues/{number}", "-f", f"body={body}"])

    def add_sub_issue(self, parent_number: int, child_issue_id: int) -> bool:
        try:
            self.run(["gh", "api", "-X", "POST", f"repos/{self.repo}/issues/{parent_number}/sub_issues",
                      "-F", f"sub_issue_id={child_issue_id}"])
            return True
        except subprocess.CalledProcessError:
            return False

    def ensure_label(self, name: str, color: str, description: str) -> None:
        try:
            self.run(["gh", "api", f"repos/{self.repo}/labels", "-f", f"name={name}", "-f", f"color={color}",
                      "-f", f"description={description}"])
        except subprocess.CalledProcessError:
            pass  # already exists

    def ensure_autolink(self, key_prefix: str, url_template: str) -> bool:
        try:
            self.run(["gh", "api", f"repos/{self.repo}/autolinks", "-f", f"key_prefix={key_prefix}",
                      "-f", f"url_template={url_template}", "-F", "is_alphanumeric=false"])
            return True
        except subprocess.CalledProcessError:
            return False  # already exists, or the user lacks admin rights on the repo

    def open_pull_request_titles(self) -> list[str]:
        pulls = json.loads(self.run(["gh", "pr", "list", "-R", self.repo, "--state", "open",
                                     "--json", "title", "--limit", "200"]))
        return [pull["title"] for pull in pulls]

    def is_issue_open(self, number: int) -> bool:
        issue = json.loads(self.run(["gh", "api", f"repos/{self.repo}/issues/{number}"]))
        return issue["state"] == "open"


# --- tasks.md parsing and tagging ---------------------------------------------------------------

def strip_tag(text: str) -> tuple[str, int | None]:
    match = EXISTING_TAG.search(text)
    if not match:
        return text.strip(), None
    return EXISTING_TAG.sub("", text, count=1).strip(), int(match.group(1))


def parse_work_items(lines: list[str], group_by: str) -> list[WorkItem]:
    items: list[WorkItem] = []
    current_section: WorkItem | None = None
    for index, line in enumerate(lines):
        section_match = SECTION_LINE.match(line)
        if section_match:
            title, tagged_number = strip_tag(section_match.group("rest"))
            current_section = WorkItem(section_match.group("key"), title, True, index, tagged_number)
            if group_by == "section":
                items.append(current_section)
            continue
        task_match = TASK_LINE.match(line)
        if not task_match:
            continue
        title, tagged_number = strip_tag(task_match.group("rest"))
        done = task_match.group("mark").lower() == "x"
        if group_by == "section" and current_section is not None:
            current_section.subtasks.append(f"- [{'x' if done else ' '}] {task_match.group('key')} {title}")
            current_section.done = current_section.done and done
        else:
            items.append(WorkItem(task_match.group("key"), title, done, index, tagged_number))
    return items


def tag_line(line: str, item_key: str, issue_number: int) -> str:
    """Insert [ISSUE-n] right after the task/section number, unless the line is already tagged."""
    if EXISTING_TAG.search(line):
        return line
    return line.replace(f"{item_key} ", f"{item_key} {issue_tag(issue_number)} ", 1) if TASK_LINE.match(line) \
        else line.replace(f"{item_key}. ", f"{item_key}. {issue_tag(issue_number)} ", 1)


# --- Sync ---------------------------------------------------------------------------------------

def proposal_title(change_dir: Path) -> str:
    proposal = change_dir / "proposal.md"
    if proposal.is_file():
        for line in proposal.read_text().splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return change_dir.name.replace("-", " ").capitalize()


def proposal_excerpt(change_dir: Path) -> str:
    proposal = change_dir / "proposal.md"
    if not proposal.is_file():
        return ""
    return "\n".join(proposal.read_text().splitlines()[:MAX_PROPOSAL_EXCERPT_LINES])


def load_mapping(change_dir: Path) -> dict:
    mapping_file = change_dir / MAPPING_FILE_NAME
    if not mapping_file.is_file():
        return {"epic": None, "items": {}}
    try:
        return json.loads(mapping_file.read_text())
    except json.JSONDecodeError as error:
        raise SyncError(f"{mapping_file} is not valid JSON: {error}") from error


def relative_change_path(change_dir: Path) -> str:
    parts = change_dir.resolve().parts
    return "/".join(parts[parts.index("openspec"):]) if "openspec" in parts else str(change_dir)


def task_issue_body(item: WorkItem, epic_number: int, change_path: str) -> str:
    subtasks = "\n".join(item.subtasks)
    return (
        f"Part of #{epic_number}\n\n"
        f"OpenSpec change: `{change_path}` — task `{item.key}`. Read `proposal.md`, `design.md` (if any) and the "
        f"delta specs there for requirements and scenarios.\n\n"
        + (f"## Subtasks\n{subtasks}\n\n" if subtasks else "")
        + "## Working on this ticket\n"
        f"- Branch: `issue-<n>-<slug>` · commits and PR title start with `[{TAG_PREFIX}-<n>]` · PR body: `Closes #<n>`\n"
        "- TDD, then `/eng:dod`, then `/eng:review` on the PR (or run `/eng:task <n>` to do it all)."
    )


def epic_body(change_dir: Path, items: list[WorkItem], change_path: str) -> str:
    checklist = []
    for item in items:
        mark = "x" if item.done else " "
        reference = f"#{item.issue_number} " if item.issue_number else ""
        checklist.append(f"- [{mark}] {reference}{item_label(item)}")
    return (
        f"OpenSpec change: `{change_path}`\n\n{proposal_excerpt(change_dir)}\n\n## Tasks\n" + "\n".join(checklist)
        + f"\n\nEach task is worked as its own PR titled `[{TAG_PREFIX}-<n>] …` (`/eng:task <n>`)."
    )


def sync_change(change_dir: Path, client: GitHubClient, repo: str, group_by: str = "task",
                dry_run: bool = False) -> SyncReport:
    tasks_file = change_dir / "tasks.md"
    if not tasks_file.is_file():
        raise SyncError(f"{tasks_file} not found — create the OpenSpec change (with tasks.md) first")

    lines = tasks_file.read_text().splitlines()
    items = parse_work_items(lines, group_by)
    mapping = load_mapping(change_dir)
    for item in items:
        item.issue_number = item.issue_number or mapping["items"].get(item.key)
    change_path = relative_change_path(change_dir)
    report = SyncReport(epic_number=mapping.get("epic"))
    epic_title = f"[EPIC] {proposal_title(change_dir)} ({change_dir.name})"

    items_to_create = [item for item in items if not item.done and item.issue_number is None]
    if dry_run:
        report.planned_titles = ([] if report.epic_number else [epic_title]) + \
            [item_label(item) for item in items_to_create]
        return report

    for label_name, (color, description) in LABELS.items():
        client.ensure_label(label_name, color, description)
    if not client.ensure_autolink(f"{TAG_PREFIX}-", f"https://github.com/{repo}/issues/<num>"):
        report.warnings.append(f"Could not add the {TAG_PREFIX}- autolink (needs repo admin); tags won't be clickable.")

    if report.epic_number is None:
        report.epic_number = client.create_issue(epic_title, "Syncing tasks…", ["epic"]).number

    for item in items_to_create:
        created = client.create_issue(item_label(item), task_issue_body(item, report.epic_number, change_path), ["task"])
        item.issue_number = created.number
        report.created_issue_numbers.append(created.number)
        if not client.add_sub_issue(report.epic_number, created.issue_id):
            report.warnings.append(f"#{created.number}: sub-issue link failed; it is still listed in the epic checklist.")

    client.update_issue_body(report.epic_number, epic_body(change_dir, items, change_path))

    for item in items:
        if item.issue_number:
            lines[item.line_index] = tag_line(lines[item.line_index], item.key, item.issue_number)
    tasks_file.write_text("\n".join(lines) + "\n")
    mapping = {"repo": repo, "epic": report.epic_number, "group_by": group_by,
               "items": {item.key: item.issue_number for item in items if item.issue_number}}
    (change_dir / MAPPING_FILE_NAME).write_text(json.dumps(mapping, indent=2) + "\n")
    return report


def next_task(change_dir: Path, client: GitHubClient) -> int | None:
    """First ticket in tasks.md order that is not done, still open, and has no open PR."""
    mapping = load_mapping(change_dir)
    items = parse_work_items((change_dir / "tasks.md").read_text().splitlines(), mapping.get("group_by", "task"))
    open_pr_titles = " ".join(client.open_pull_request_titles())
    for item in items:
        number = item.issue_number or mapping["items"].get(item.key)
        if item.done or number is None or issue_tag(number) in open_pr_titles:
            continue
        if client.is_issue_open(number):
            return number
    return None


# --- CLI ----------------------------------------------------------------------------------------

def detect_repo() -> str:
    return run_command(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    sync_parser = commands.add_parser("sync")
    sync_parser.add_argument("--change", required=True)
    sync_parser.add_argument("--group-by", choices=["task", "section"], default="task")
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument("--repo")
    next_parser = commands.add_parser("next")
    next_parser.add_argument("--change", required=True)
    next_parser.add_argument("--repo")
    branch_parser = commands.add_parser("branch")
    branch_parser.add_argument("--issue", type=int, required=True)
    branch_parser.add_argument("--title", required=True)
    title_parser = commands.add_parser("title")
    title_parser.add_argument("--issue", type=int, required=True)
    title_parser.add_argument("--type", default="feat")
    title_parser.add_argument("--title", required=True)
    arguments = parser.parse_args()

    if arguments.command == "branch":
        print(branch_name(arguments.issue, arguments.title))
        return 0
    if arguments.command == "title":
        print(pr_title(arguments.issue, arguments.type, arguments.title))
        return 0

    change_dir = Path(arguments.change)
    repo = arguments.repo or load_mapping(change_dir).get("repo") or detect_repo()
    client = GhCliClient(repo)
    try:
        if arguments.command == "next":
            number = next_task(change_dir, client)
            print(number if number else "none")
            return 0
        report = sync_change(change_dir, client, repo, arguments.group_by, arguments.dry_run)
    except SyncError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if arguments.dry_run:
        print("Would create:\n" + "\n".join(f"  {title}" for title in report.planned_titles) if report.planned_titles
              else "Nothing to create.")
        return 0
    print(f"Epic: #{report.epic_number}  (https://github.com/{repo}/issues/{report.epic_number})")
    print("Created: " + (", ".join(f"#{n}" for n in report.created_issue_numbers) or "nothing new"))
    for warning in report.warnings:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
