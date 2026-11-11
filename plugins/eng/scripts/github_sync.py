#!/usr/bin/env python3
"""
Tags: `[<KIND>-<n>]` where KIND comes from the issue's native type (org repos), else a type label
(bug → BUG, feature/enhancement → FEATURE, task → TASK, story → STORY, chore → CHORE, spike → SPIKE), else ISSUE.

Syncs an OpenSpec change to GitHub: one task issue per open task in tasks.md, grouped by
  - milestone (default): one milestone per change + a `change:<name>` label — works on free personal accounts;
  - epic: a parent issue labelled `epic` with the tasks as sub-issues;
  - both. Tags every task in tasks.md with [ISSUE-<n>] and records the mapping in
<change>/github.json so re-running only creates what is new.

GitHub is reached through the GitHubClient port; GhCliClient is the adapter that uses the `gh` CLI.

Usage:
  github_sync.py sync   --change openspec/changes/<name> [--tracking milestone|epic|both] [--group-by task|section]
                        [--dry-run] [--repo owner/name]
  github_sync.py next   --change openspec/changes/<name>       # prints the next issue number to work on
  github_sync.py tag    --issue 43                              # [TASK-43] / [BUG-43] / [ISSUE-43] …
  github_sync.py branch --issue 43 --title "POST /refunds endpoint"
  github_sync.py title  --issue 43 --type feat --title "POST /refunds endpoint"
  (tag/branch/title look the kind up from the issue's type or labels; pass --kind BUG to skip the lookup)
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from openspec_model import TASK_ANNOTATION  # noqa: E402  (shared with spec_lint / trace)

DEFAULT_KIND = "ISSUE"  # tag kind when the issue has no type and no type label
# Label → tag kind, in priority order (an issue labelled both bug and task is a BUG).
KIND_BY_LABEL = [
    ({"bug", "defect"}, "BUG"),
    ({"feature", "enhancement", "feat"}, "FEATURE"),
    ({"story", "user story", "user-story"}, "STORY"),
    ({"spike", "research"}, "SPIKE"),
    ({"chore", "maintenance"}, "CHORE"),
    ({"task"}, "TASK"),
]
KIND_ALIASES = {"USERSTORY": "STORY", "ENHANCEMENT": "FEATURE", "DEFECT": "BUG"}
KNOWN_KINDS = [DEFAULT_KIND, "TASK", "BUG", "FEATURE", "STORY", "CHORE", "SPIKE"]  # get autolinks
MAPPING_FILE_NAME = "github.json"
MAX_BRANCH_LENGTH = 60
MAX_PROPOSAL_EXCERPT_LINES = 40

TASK_LINE = re.compile(r"^(?P<indent>\s*)- \[(?P<mark>[ xX])\] (?P<key>\d+(?:\.\d+)+)\s+(?P<rest>.*)$")
SECTION_LINE = re.compile(r"^## (?P<key>\d+)\.\s+(?P<rest>.*)$")
EXISTING_TAG = re.compile(r"\[[A-Z][A-Z0-9]*-(\d+)\]\s*")  # [ISSUE-12], [TASK-44], [BUG-10] …

TRACKING_MODES = ("milestone", "epic", "both")
CHANGE_LABEL_COLOR = "1d76db"
TASK_KIND = "TASK"  # tickets created by sync carry the `task` label
SIZE_LABEL_COLOR = "c5def5"

LABELS = {
    "epic": ("5319e7", "OpenSpec change tracked as an epic"),
    "task": ("0e8a16", "Task from an OpenSpec change"),
}


# --- Domain ----------------------------------------------------------------------------------

class SyncError(Exception):
    """The change cannot be synced (missing files, unreadable mapping)."""


class ClaimError(Exception):
    """The ticket is already assigned to someone else."""


@dataclass
class StatusRow:
    key: str
    title: str
    issue_number: int | None
    state: str  # done · in review · in progress · blocked · ready
    who: str = ""
    pull_request: int | None = None
    waiting_for: list[int] = field(default_factory=list)


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
    after: list[str] = field(default_factory=list)  # keys of tasks that must be done first: "(after: 1.1, 1.2)"
    size: str | None = None                         # "(size: S)" → label size:S


@dataclass
class SyncReport:
    epic_number: int | None = None
    milestone_number: int | None = None
    created_issue_numbers: list[int] = field(default_factory=list)
    planned_titles: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def item_label(item: WorkItem) -> str:
    """'1.1 Title' for tasks, '1. Title' for sections — matching how they read in tasks.md."""
    separator = "" if "." in item.key else "."
    return f"{item.key}{separator} {item.title}"


def tag_kind(issue_type: str | None, labels: list[str]) -> str:
    """Tag kind for an issue: its native issue type (org repos), else a type label, else ISSUE."""
    if issue_type:
        kind = re.sub(r"[^A-Z0-9]", "", issue_type.upper())
        return KIND_ALIASES.get(kind, kind) or DEFAULT_KIND
    lowered = {label.lower() for label in labels}
    for label_names, kind in KIND_BY_LABEL:
        if lowered & label_names:
            return kind
    return DEFAULT_KIND


def issue_tag(issue_number: int, kind: str = DEFAULT_KIND) -> str:
    return f"[{kind}-{issue_number}]"


def branch_name(issue_number: int, title: str, kind: str = DEFAULT_KIND) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    prefix = f"{kind.lower()}-{issue_number}-"
    return (prefix + slug)[:MAX_BRANCH_LENGTH].rstrip("-")


def pr_title(issue_number: int, change_type: str, title: str, kind: str = DEFAULT_KIND) -> str:
    return f"{issue_tag(issue_number, kind)} {change_type}: {title}"


def has_tag_for(issue_number: int, text: str) -> bool:
    """True when text contains a tag of any kind for this issue number."""
    return re.search(rf"\[[A-Z][A-Z0-9]*-{issue_number}\]", text) is not None


# --- Port and adapter --------------------------------------------------------------------------

class GitHubClient(Protocol):
    def create_issue(self, title: str, body: str, labels: list[str], milestone: int | None = None) -> CreatedIssue: ...
    def ensure_milestone(self, title: str, description: str) -> int: ...
    def update_issue_body(self, number: int, body: str) -> None: ...
    def add_sub_issue(self, parent_number: int, child_issue_id: int) -> bool: ...
    def ensure_label(self, name: str, color: str, description: str) -> None: ...
    def ensure_autolink(self, key_prefix: str, url_template: str) -> bool: ...
    def open_pull_request_titles(self) -> list[str]: ...
    def is_issue_open(self, number: int) -> bool: ...
    def issue_type_and_labels(self, number: int) -> tuple[str | None, list[str]]: ...
    def open_pull_requests(self) -> list[dict]: ...  # {"number", "title", "author", "draft"}
    def issue_body(self, number: int) -> str: ...
    def issue_id(self, number: int) -> int: ...
    def add_blocked_by(self, number: int, blocking_issue_id: int) -> bool: ...
    def blocked_by(self, number: int) -> list[int]: ...
    def assignees(self, number: int) -> list[str]: ...
    def add_assignee(self, number: int, login: str) -> None: ...
    def current_login(self) -> str: ...


def run_command(command: list[str]) -> str:
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout


class GhCliClient:
    """GitHubClient adapter backed by the `gh` CLI (uses the user's existing gh authentication)."""

    def __init__(self, repo: str, run: Callable[[list[str]], str] = run_command):
        self.repo = repo
        self.run = run

    def create_issue(self, title: str, body: str, labels: list[str], milestone: int | None = None) -> CreatedIssue:
        command = ["gh", "api", f"repos/{self.repo}/issues", "-f", f"title={title}", "-f", f"body={body}"]
        for label in labels:
            command += ["-f", f"labels[]={label}"]
        if milestone is not None:
            command += ["-F", f"milestone={milestone}"]
        created = json.loads(self.run(command))
        return CreatedIssue(number=created["number"], issue_id=created["id"])

    def ensure_milestone(self, title: str, description: str) -> int:
        """Reuse the milestone with this exact title (open or closed), otherwise create it."""
        existing = json.loads(self.run(["gh", "api", f"repos/{self.repo}/milestones?state=all&per_page=100"]))
        for milestone in existing:
            if milestone["title"] == title:
                self.run(["gh", "api", "-X", "PATCH", f"repos/{self.repo}/milestones/{milestone['number']}",
                          "-f", f"description={description}"])
                return milestone["number"]
        created = json.loads(self.run(["gh", "api", f"repos/{self.repo}/milestones", "-f", f"title={title}",
                                       "-f", f"description={description}"]))
        return created["number"]

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

    def _issue(self, number: int) -> dict:
        return json.loads(self.run(["gh", "api", f"repos/{self.repo}/issues/{number}"]))

    def open_pull_requests(self) -> list[dict]:
        pulls = json.loads(self.run(["gh", "pr", "list", "-R", self.repo, "--state", "open",
                                     "--json", "number,title,author,isDraft", "--limit", "200"]))
        return [{"number": pull["number"], "title": pull["title"], "author": (pull.get("author") or {}).get("login", "?"),
                 "draft": pull.get("isDraft", False)} for pull in pulls]

    def issue_body(self, number: int) -> str:
        return self._issue(number).get("body") or ""

    def issue_id(self, number: int) -> int:
        return self._issue(number)["id"]

    def add_blocked_by(self, number: int, blocking_issue_id: int) -> bool:
        try:
            self.run(["gh", "api", "-X", "POST", f"repos/{self.repo}/issues/{number}/dependencies/blocked_by",
                      "-F", f"issue_id={blocking_issue_id}"])
            return True
        except subprocess.CalledProcessError:
            return False  # already linked, or native dependencies unavailable

    def blocked_by(self, number: int) -> list[int]:
        try:
            blocking = json.loads(self.run(["gh", "api", f"repos/{self.repo}/issues/{number}/dependencies/blocked_by"]))
        except subprocess.CalledProcessError:
            return []
        return [issue["number"] for issue in blocking]

    def assignees(self, number: int) -> list[str]:
        return [person["login"] for person in self._issue(number).get("assignees", [])]

    def add_assignee(self, number: int, login: str) -> None:
        self.run(["gh", "api", "-X", "POST", f"repos/{self.repo}/issues/{number}/assignees", "-f", f"assignees[]={login}"])

    def current_login(self) -> str:
        return json.loads(self.run(["gh", "api", "user"]))["login"]

    def issue_type_and_labels(self, number: int) -> tuple[str | None, list[str]]:
        issue = self._issue(number)
        issue_type = (issue.get("type") or {}).get("name")  # native issue types exist only on org repos
        return issue_type, [label["name"] for label in issue.get("labels", [])]


def tag_for_issue(client: GitHubClient, issue_number: int) -> str:
    return issue_tag(issue_number, tag_kind(*client.issue_type_and_labels(issue_number)))


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
        title, after, size = split_annotation(title)
        done = task_match.group("mark").lower() == "x"
        if group_by == "section" and current_section is not None:
            current_section.subtasks.append(f"- [{'x' if done else ' '}] {task_match.group('key')} {title}")
            current_section.done = current_section.done and done
            for dependency in after:  # a task depending on another section makes the whole section depend on it
                dependency_section = dependency.split(".")[0]
                if dependency_section != current_section.key and dependency_section not in current_section.after:
                    current_section.after.append(dependency_section)
        else:
            items.append(WorkItem(task_match.group("key"), title, done, index, tagged_number, after=after, size=size))
    return items


def split_annotation(title: str) -> tuple[str, list[str], str | None]:
    """'POST /refunds (after: 1.1; size: M)' → ('POST /refunds', ['1.1'], 'M')."""
    annotation = TASK_ANNOTATION.search(title)
    if not annotation:
        return title, [], None
    after, size = [], None
    for part in annotation.group("body").split(";"):
        name, _, value = part.partition(":")
        if name.strip().lower() == "after":
            after = [key.strip() for key in value.split(",") if key.strip()]
        elif name.strip().lower() == "size":
            size = value.strip().upper()
    return title[:annotation.start()].strip(), after, size


def tag_line(line: str, item_key: str, issue_number: int, kind: str = DEFAULT_KIND) -> str:
    """Insert [<KIND>-n] right after the task/section number, unless the line is already tagged."""
    if EXISTING_TAG.search(line):
        return line
    tag = issue_tag(issue_number, kind)
    return line.replace(f"{item_key} ", f"{item_key} {tag} ", 1) if TASK_LINE.match(line) \
        else line.replace(f"{item_key}. ", f"{item_key}. {tag} ", 1)


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


def task_issue_body(item: WorkItem, parent_lines: list[str], change_path: str,
                    dependency_numbers: list[int] | None = None) -> str:
    subtasks = "\n".join(item.subtasks)
    dependency_lines = [f"Depends on #{number}" for number in dependency_numbers or []]
    return (
        "\n".join(parent_lines + dependency_lines) + "\n\n"
        f"OpenSpec change: `{change_path}` — task `{item.key}`. Read `proposal.md`, `design.md` (if any) and the "
        f"delta specs there for requirements and scenarios.\n\n"
        + (f"## Subtasks\n{subtasks}\n\n" if subtasks else "")
        + "## Working on this ticket\n"
        f"- Tag `[{TASK_KIND}-<n>]` (from the `task` label): branch `{TASK_KIND.lower()}-<n>-<slug>` · every commit and the PR title start with the tag · PR body: `Closes #<n>`\n"
        "- PR body: acceptance criteria, Definition of Done and pending decisions as checklists — it can only be marked\n"
        "  ready when all are checked (CI enforces). Run `/eng:task <n>` to do it all."
    )


def epic_body(change_dir: Path, items: list[WorkItem], change_path: str) -> str:
    checklist = []
    for item in items:
        mark = "x" if item.done else " "
        reference = f"#{item.issue_number} " if item.issue_number else ""
        checklist.append(f"- [{mark}] {reference}{item_label(item)}")
    return (
        f"OpenSpec change: `{change_path}`\n\n{proposal_excerpt(change_dir)}\n\n## Tasks\n" + "\n".join(checklist)
        + f"\n\nEach task is worked as its own PR titled `[{TASK_KIND}-<n>] …` (`/eng:task <n>`)."
    )


DEPENDS_ON_LINE = re.compile(r"(?im)^Depends on #(\d+)\s*$")


def with_dependency_lines(body: str, dependency_numbers: list[int]) -> str:
    """Body with a 'Depends on #n' line for every dependency (existing lines kept, missing ones prepended)."""
    present = {int(number) for number in DEPENDS_ON_LINE.findall(body)}
    missing = [f"Depends on #{number}" for number in dependency_numbers if number not in present]
    return "\n".join(missing + [body]) if missing else body


def link_planned_dependencies(client: GitHubClient, items: list[WorkItem], numbers_by_key: dict[str, int],
                              report: SyncReport) -> None:
    """Make every planned `after:` dependency a native 'blocked by' link and a 'Depends on' line on the ticket."""
    native_supported = True
    for item in items:
        if item.done or not item.issue_number or not item.after:
            continue
        wanted = [numbers_by_key[key] for key in item.after if key in numbers_by_key]
        existing_links = set(client.blocked_by(item.issue_number))
        for dependency in wanted:
            if dependency not in existing_links and native_supported:
                native_supported = client.add_blocked_by(item.issue_number, client.issue_id(dependency))
        body = client.issue_body(item.issue_number)
        updated = with_dependency_lines(body, wanted)
        if updated != body:
            client.update_issue_body(item.issue_number, updated)
    if not native_supported:
        report.warnings.append("Native blocked-by dependencies are unavailable here; dependencies are kept as "
                               "'Depends on #n' lines in the tickets instead.")


def tick_closed_tasks(client: GitHubClient, items: list[WorkItem], lines: list[str]) -> None:
    """A closed ticket means its PR was merged: tick its task — or every task of its section — in tasks.md
    (PRs never edit tasks.md, so parallel PRs can't conflict on it)."""
    for item in items:
        if item.done or not item.issue_number or client.is_issue_open(item.issue_number):
            continue
        if TASK_LINE.match(lines[item.line_index]):
            lines[item.line_index] = lines[item.line_index].replace("- [ ]", "- [x]", 1)
        else:  # section heading: tick every task until the next section
            index = item.line_index + 1
            while index < len(lines) and not SECTION_LINE.match(lines[index]):
                if TASK_LINE.match(lines[index]):
                    lines[index] = lines[index].replace("- [ ]", "- [x]", 1)
                index += 1
        item.done = True


def block(client: GitHubClient, issue_number: int, by: int) -> bool:
    """Record a dependency discovered during the work — on GitHub only, so tasks.md never conflicts."""
    native = client.add_blocked_by(issue_number, client.issue_id(by))
    body = client.issue_body(issue_number)
    updated = with_dependency_lines(body, [by])
    if updated != body:
        client.update_issue_body(issue_number, updated)
    return native


def claim(client: GitHubClient, issue_number: int, force: bool = False) -> str:
    """Assign the ticket to me before starting, so a teammate's `next` skips it."""
    me = client.current_login()
    others = [person for person in client.assignees(issue_number) if person != me]
    if others and not force:
        raise ClaimError(f"#{issue_number} is assigned to {', '.join(others)} — coordinate first, or use --force")
    if me not in client.assignees(issue_number):
        client.add_assignee(issue_number, me)
    return me


def milestone_description(change_dir: Path, change_path: str) -> str:
    first_paragraph = next((block.strip() for block in proposal_excerpt(change_dir).split("\n\n")[1:] if block.strip()), "")
    return f"OpenSpec change {change_path}. {first_paragraph}".strip()[:1000]


def resolve_tracking(requested: str | None, mapping: dict) -> str:
    """Explicit choice wins; otherwise keep what the change was synced with (2.0 mappings had only an epic)."""
    if requested:
        return requested
    if mapping.get("tracking"):
        return mapping["tracking"]
    return "epic" if mapping.get("epic") else "milestone"


def resolve_group_by(requested: str | None, mapping: dict) -> str:
    """Explicit choice wins; a change keeps the granularity it was synced with; new changes get one PR per section."""
    if requested:
        return requested
    if mapping.get("group_by"):
        return mapping["group_by"]
    return "task" if mapping.get("items") else "section"


def sync_change(change_dir: Path, client: GitHubClient, repo: str, group_by: str | None = None,
                dry_run: bool = False, tracking: str | None = None) -> SyncReport:
    tasks_file = change_dir / "tasks.md"
    if not tasks_file.is_file():
        raise SyncError(f"{tasks_file} not found — create the OpenSpec change (with tasks.md) first")

    lines = tasks_file.read_text().splitlines()
    mapping = load_mapping(change_dir)
    group_by = resolve_group_by(group_by, mapping)
    items = parse_work_items(lines, group_by)
    tracking = resolve_tracking(tracking, mapping)
    if tracking not in TRACKING_MODES:
        raise SyncError(f"unknown tracking mode {tracking!r}; use one of {', '.join(TRACKING_MODES)}")
    use_milestone, use_epic = tracking in ("milestone", "both"), tracking in ("epic", "both")
    for item in items:
        item.issue_number = item.issue_number or mapping["items"].get(item.key)
    change_path = relative_change_path(change_dir)
    change_title = f"{proposal_title(change_dir)} ({change_dir.name})"
    change_label = f"change:{change_dir.name}"
    report = SyncReport(epic_number=mapping.get("epic"), milestone_number=mapping.get("milestone"))
    epic_title = f"[EPIC] {change_title}"

    items_to_create = [item for item in items if not item.done and item.issue_number is None]
    if dry_run:
        report.planned_titles = (
            ([f"Milestone: {change_title}"] if use_milestone and not report.milestone_number else [])
            + ([epic_title] if use_epic and not report.epic_number else [])
            + [item_label(item) for item in items_to_create]
        )
        return report

    for label_name, (color, description) in LABELS.items():
        client.ensure_label(label_name, color, description)
    client.ensure_label(change_label, CHANGE_LABEL_COLOR, f"OpenSpec change {change_dir.name}")
    for kind in KNOWN_KINDS:
        if not client.ensure_autolink(f"{kind}-", f"https://github.com/{repo}/issues/<num>"):
            report.warnings.append(f"Could not add the {kind}- autolink (needs repo admin); those tags won't be clickable.")
            break

    if use_milestone:
        report.milestone_number = client.ensure_milestone(change_title, milestone_description(change_dir, change_path))
    if use_epic and report.epic_number is None:
        report.epic_number = client.create_issue(epic_title, "Syncing tasks…", ["epic", change_label],
                                                 report.milestone_number).number

    parent_lines = ([f"Part of #{report.epic_number}"] if use_epic else []) + \
                   ([f"Milestone: {change_title}"] if use_milestone else [])
    numbers_by_key = {item.key: item.issue_number for item in items if item.issue_number}
    for size in sorted({item.size for item in items_to_create if item.size}):
        client.ensure_label(f"size:{size}", SIZE_LABEL_COLOR, f"Task size {size}")
    for item in items_to_create:
        dependency_numbers = [numbers_by_key[key] for key in item.after if key in numbers_by_key]
        labels = ["task", change_label] + ([f"size:{item.size}"] if item.size else [])
        created = client.create_issue(item_label(item),
                                      task_issue_body(item, parent_lines, change_path, dependency_numbers),
                                      labels, report.milestone_number if use_milestone else None)
        numbers_by_key[item.key] = created.number
        item.issue_number = created.number
        report.created_issue_numbers.append(created.number)
        if use_epic and not client.add_sub_issue(report.epic_number, created.issue_id):
            report.warnings.append(f"#{created.number}: sub-issue link failed; it is still listed in the epic checklist.")

    numbers_by_key.update({item.key: item.issue_number for item in items if item.issue_number})
    link_planned_dependencies(client, items, numbers_by_key, report)
    tick_closed_tasks(client, items, lines)

    if use_epic:
        client.update_issue_body(report.epic_number, epic_body(change_dir, items, change_path))

    for item in items:
        if item.issue_number:
            lines[item.line_index] = tag_line(lines[item.line_index], item.key, item.issue_number, TASK_KIND)
    tasks_file.write_text("\n".join(lines) + "\n")
    mapping = {"repo": repo, "tracking": tracking, "milestone": report.milestone_number if use_milestone else None,
               "epic": report.epic_number if use_epic else None, "group_by": group_by,
               "items": {item.key: item.issue_number for item in items if item.issue_number}}
    (change_dir / MAPPING_FILE_NAME).write_text(json.dumps(mapping, indent=2) + "\n")
    return report


def _items_with_numbers(change_dir: Path) -> list[WorkItem]:
    mapping = load_mapping(change_dir)
    items = parse_work_items((change_dir / "tasks.md").read_text().splitlines(), mapping.get("group_by", "task"))
    for item in items:
        item.issue_number = item.issue_number or mapping["items"].get(item.key)
    return items


def _dependency_numbers(item: WorkItem, items_by_key: dict[str, WorkItem], client: GitHubClient) -> set[int]:
    """Planned (tasks.md `after:`) + discovered (native blocked-by links, 'Depends on #n' lines) dependencies."""
    planned = {items_by_key[key].issue_number for key in item.after if key in items_by_key and items_by_key[key].issue_number}
    discovered = set(client.blocked_by(item.issue_number))
    discovered |= {int(number) for number in DEPENDS_ON_LINE.findall(client.issue_body(item.issue_number))}
    return planned | discovered


def _unfinished_dependencies(item: WorkItem, items_by_key: dict[str, WorkItem], client: GitHubClient) -> list[int]:
    """Dependencies that are neither ticked in tasks.md nor closed (= merged) on GitHub."""
    done_numbers = {other.issue_number for other in items_by_key.values() if other.done and other.issue_number}
    return sorted(number for number in _dependency_numbers(item, items_by_key, client)
                  if number not in done_numbers and client.is_issue_open(number))


def blocked_tasks(change_dir: Path, client: GitHubClient) -> dict[int, list[int]]:
    """Open tickets whose dependencies are not finished yet → the tickets they wait for."""
    items = _items_with_numbers(change_dir)
    items_by_key = {item.key: item for item in items}
    blocked = {}
    for item in items:
        if item.done or item.issue_number is None or not client.is_issue_open(item.issue_number):
            continue
        waiting_for = _unfinished_dependencies(item, items_by_key, client)
        if waiting_for:
            blocked[item.issue_number] = waiting_for
    return blocked


def next_task(change_dir: Path, client: GitHubClient) -> int | None:
    """Next ticket to work on: my own unfinished claim first, else the first unclaimed ticket in tasks.md order that
    is open, has no open PR and no unfinished dependency."""
    items = _items_with_numbers(change_dir)
    items_by_key = {item.key: item for item in items}
    open_pr_titles = " ".join(client.open_pull_request_titles())
    me = client.current_login()
    mine, unclaimed = [], []
    for item in items:
        number = item.issue_number
        if item.done or number is None or has_tag_for(number, open_pr_titles) or not client.is_issue_open(number):
            continue
        if _unfinished_dependencies(item, items_by_key, client):
            continue
        assigned = client.assignees(number)
        if me in assigned:
            mine.append(number)
        elif not assigned:
            unclaimed.append(number)
    return (mine or unclaimed or [None])[0]


def status(change_dir: Path, client: GitHubClient) -> list[StatusRow]:
    """One row per ticket: done · in review · in progress · blocked · ready, with who and what it waits for."""
    items = _items_with_numbers(change_dir)
    items_by_key = {item.key: item for item in items}
    pulls = client.open_pull_requests()
    rows = []
    for item in items:
        number = item.issue_number
        row = StatusRow(item.key, item.title, number, "ready")
        if number is None:
            row.state = "done" if item.done else "not synced"
            rows.append(row)
            continue
        pull = next((pull for pull in pulls if has_tag_for(number, pull["title"])), None)
        assigned = client.assignees(number)
        row.who = pull["author"] if pull else ", ".join(assigned)
        row.pull_request = pull["number"] if pull else None
        if item.done or not client.is_issue_open(number):
            row.state = "done"
        elif pull and not pull["draft"]:
            row.state = "in review"
        elif pull or assigned:
            row.state = "in progress"
        else:
            row.waiting_for = _unfinished_dependencies(item, items_by_key, client)
            row.state = "blocked" if row.waiting_for else "ready"
        rows.append(row)
    return rows


# --- CLI ----------------------------------------------------------------------------------------

def detect_repo() -> str:
    return run_command(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    sync_parser = commands.add_parser("sync")
    sync_parser.add_argument("--change", required=True)
    sync_parser.add_argument("--group-by", choices=["task", "section"],
                             help="default: section (one PR per '## N.' section), or what the change used before")
    sync_parser.add_argument("--tracking", choices=TRACKING_MODES, help="default: milestone (or what the change used before)")
    sync_parser.add_argument("--dry-run", action="store_true")
    sync_parser.add_argument("--repo")
    next_parser = commands.add_parser("next")
    next_parser.add_argument("--change", required=True)
    next_parser.add_argument("--repo")
    status_parser = commands.add_parser("status", help="board: done / in review / in progress / blocked / ready")
    status_parser.add_argument("--change", required=True)
    status_parser.add_argument("--repo")
    claim_parser = commands.add_parser("claim", help="assign the ticket to me before starting")
    claim_parser.add_argument("--issue", type=int, required=True)
    claim_parser.add_argument("--force", action="store_true")
    claim_parser.add_argument("--repo")
    block_parser = commands.add_parser("block", help="record a dependency discovered during the work")
    block_parser.add_argument("--issue", type=int, required=True)
    block_parser.add_argument("--by", type=int, required=True)
    block_parser.add_argument("--repo")
    tag_parser = commands.add_parser("tag", help="print the tag for an issue, e.g. [BUG-10]")
    branch_parser = commands.add_parser("branch")
    title_parser = commands.add_parser("title")
    for issue_parser in (tag_parser, branch_parser, title_parser):
        issue_parser.add_argument("--issue", type=int, required=True)
        issue_parser.add_argument("--kind", help="BUG, FEATURE, TASK, … (default: looked up from the issue's type/labels)")
        issue_parser.add_argument("--repo")
    branch_parser.add_argument("--title", required=True)
    title_parser.add_argument("--type", default="feat")
    title_parser.add_argument("--title", required=True)
    arguments = parser.parse_args()

    if arguments.command in ("tag", "branch", "title"):
        kind = arguments.kind.upper() if arguments.kind else \
            tag_kind(*GhCliClient(arguments.repo or detect_repo()).issue_type_and_labels(arguments.issue))
        if arguments.command == "tag":
            print(issue_tag(arguments.issue, kind))
        elif arguments.command == "branch":
            print(branch_name(arguments.issue, arguments.title, kind))
        else:
            print(pr_title(arguments.issue, arguments.type, arguments.title, kind))
        return 0

    if arguments.command in ("claim", "block"):
        client = GhCliClient(arguments.repo or detect_repo())
        if arguments.command == "block":
            native = block(client, arguments.issue, arguments.by)
            print(f"#{arguments.issue} now depends on #{arguments.by}" + ("" if native else " (body note only — native links unavailable)"))
            return 0
        try:
            print(f"#{arguments.issue} assigned to {claim(client, arguments.issue, arguments.force)}")
        except ClaimError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
        return 0

    change_dir = Path(arguments.change)
    repo = arguments.repo or load_mapping(change_dir).get("repo") or detect_repo()
    client = GhCliClient(repo)
    try:
        if arguments.command == "status":
            icons = {"done": "✅", "in review": "👀", "in progress": "🔨", "blocked": "⛔", "ready": "🟢", "not synced": "·"}
            rows = status(change_dir, client)
            for row in rows:
                detail = f" — waits for {', '.join(f'#{n}' for n in row.waiting_for)}" if row.waiting_for else ""
                pr = f" PR #{row.pull_request}" if row.pull_request else ""
                print(f"{icons.get(row.state, '?')} {row.state:<11} #{row.issue_number or '-':<5} {row.key:<5} {row.title}"
                      f"{f' ({row.who})' if row.who else ''}{pr}{detail}")
            ready = sum(row.state == "ready" for row in rows)
            print(f"Ready to start now: {ready} · in progress/review: "
                  f"{sum(row.state in ('in progress', 'in review') for row in rows)} · blocked: "
                  f"{sum(row.state == 'blocked' for row in rows)} · done: {sum(row.state == 'done' for row in rows)}/{len(rows)}")
            return 0
        if arguments.command == "next":
            number = next_task(change_dir, client)
            print(number if number else "none")
            if not number:
                for waiting, blockers in blocked_tasks(change_dir, client).items():
                    print(f"blocked: #{waiting} waits for {', '.join(f'#{n}' for n in blockers)}")
            return 0
        report = sync_change(change_dir, client, repo, arguments.group_by, arguments.dry_run, arguments.tracking)
    except SyncError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if arguments.dry_run:
        print("Would create:\n" + "\n".join(f"  {title}" for title in report.planned_titles) if report.planned_titles
              else "Nothing to create.")
        return 0
    if report.milestone_number:
        print(f"Milestone: https://github.com/{repo}/milestone/{report.milestone_number}")
    if report.epic_number:
        print(f"Epic issue: https://github.com/{repo}/issues/{report.epic_number}")
    print("Created: " + (", ".join(f"#{n}" for n in report.created_issue_numbers) or "nothing new"))
    for warning in report.warnings:
        print(f"warning: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
