"""Behaviour tests for github_sync.py — OpenSpec change → GitHub epic + one linked issue per task.

GitHub is reached only through the GitHubClient port; these tests use an in-memory fake, so no network is used.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/github_sync.py"
spec = importlib.util.spec_from_file_location("github_sync", SCRIPT)
github_sync = importlib.util.module_from_spec(spec)
sys.modules["github_sync"] = github_sync  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(github_sync)

TASKS_MD = """# Tasks

## 1. Data model
- [ ] 1.1 Add refunds table migration
- [x] 1.2 Add Refund entity

## 2. API
- [ ] 2.1 POST /refunds endpoint
- [ ] 2.2 Reject refunds above the order total
"""


class FakeGitHubClient:
    """In-memory stand-in for GitHub. Issue ids are number * 1000 to catch number/id mix-ups."""

    def __init__(self, sub_issues_supported: bool = True):
        self.issues: dict[int, dict] = {}
        self.sub_issue_links: list[tuple[int, int]] = []
        self.labels: set[str] = set()
        self.autolinks: list[str] = []
        self.sub_issues_supported = sub_issues_supported
        self.open_pr_titles: list[str] = []
        self.closed_issue_numbers: set[int] = set()
        self.milestones: dict[int, dict] = {}

    def create_issue(self, title, body, labels, milestone=None):
        number = len(self.issues) + 100
        self.issues[number] = {"title": title, "body": body, "labels": list(labels), "milestone": milestone}
        return github_sync.CreatedIssue(number=number, issue_id=number * 1000)

    def ensure_milestone(self, title, description):
        for number, milestone in self.milestones.items():
            if milestone["title"] == title:
                milestone["description"] = description
                return number
        number = len(self.milestones) + 1
        self.milestones[number] = {"title": title, "description": description}
        return number

    def update_issue_body(self, number, body):
        self.issues[number]["body"] = body

    def add_sub_issue(self, parent_number, child_issue_id):
        if not self.sub_issues_supported:
            return False
        self.sub_issue_links.append((parent_number, child_issue_id))
        return True

    def ensure_label(self, name, color, description):
        self.labels.add(name)

    def ensure_autolink(self, key_prefix, url_template):
        self.autolinks.append(key_prefix)
        return True

    def open_pull_request_titles(self):
        return list(self.open_pr_titles)

    def is_issue_open(self, number):
        return number not in self.closed_issue_numbers


@pytest.fixture
def change_dir(tmp_path):
    directory = tmp_path / "openspec/changes/add-refunds"
    directory.mkdir(parents=True)
    (directory / "proposal.md").write_text("# Add refunds\n\n## Why\nCustomers need refunds.\n")
    (directory / "tasks.md").write_text(TASKS_MD)
    return directory


def sync(change_dir, client, **options):
    """Parent-issue mode (tracking="epic") — the pre-2.1 behaviour most tests below cover."""
    options.setdefault("tracking", "epic")
    return github_sync.sync_change(change_dir, client, repo="acme/shop", **options)


def sync_default(change_dir, client, **options):
    return github_sync.sync_change(change_dir, client, repo="acme/shop", **options)


def task_issues(client):
    return {number: issue for number, issue in client.issues.items() if "task" in issue["labels"]}


def epic_issues(client):
    return {number: issue for number, issue in client.issues.items() if "epic" in issue["labels"]}


# --- tag / branch / title helpers ---------------------------------------------------------

def test_issue_tag_branch_and_pr_title_formats():
    assert github_sync.issue_tag(43) == "[ISSUE-43]"
    assert github_sync.branch_name(43, "POST /refunds endpoint!") == "issue-43-post-refunds-endpoint"
    assert len(github_sync.branch_name(43, "word " * 40)) <= 60
    assert github_sync.pr_title(43, "feat", "POST /refunds endpoint") == "[ISSUE-43] feat: POST /refunds endpoint"


# --- sync ----------------------------------------------------------------------------------

def test_creates_epic_and_one_issue_per_open_task(change_dir):
    client = FakeGitHubClient()

    report = sync(change_dir, client)

    assert len(epic_issues(client)) == 1
    epic = next(iter(epic_issues(client).values()))
    assert "Add refunds" in epic["title"] and "add-refunds" in epic["title"]
    titles = sorted(issue["title"] for issue in task_issues(client).values())
    assert titles == ["1.1 Add refunds table migration", "2.1 POST /refunds endpoint", "2.2 Reject refunds above the order total"]
    assert len(report.created_issue_numbers) == 3


def test_completed_tasks_get_no_ticket_but_appear_checked_in_epic(change_dir):
    client = FakeGitHubClient()

    sync(change_dir, client)

    epic_body = next(iter(epic_issues(client).values()))["body"]
    assert "- [x] 1.2 Add Refund entity" in epic_body
    assert not any("1.2" in issue["title"] for issue in task_issues(client).values())


def test_task_issues_are_linked_as_sub_issues_and_reference_the_epic(change_dir):
    client = FakeGitHubClient()

    sync(change_dir, client)

    epic_number = next(iter(epic_issues(client)))
    assert sorted(client.sub_issue_links) == sorted((epic_number, n * 1000) for n in task_issues(client))
    for issue in task_issues(client).values():
        assert f"Part of #{epic_number}" in issue["body"]
        assert "openspec/changes/add-refunds" in issue["body"]


def test_epic_body_lists_task_issues_as_checklist(change_dir):
    client = FakeGitHubClient()

    sync(change_dir, client)

    epic_body = next(iter(epic_issues(client).values()))["body"]
    for number, issue in task_issues(client).items():
        assert f"- [ ] #{number} {issue['title']}" in epic_body


def test_writes_tags_into_tasks_md_and_mapping_file(change_dir):
    client = FakeGitHubClient()

    sync(change_dir, client)

    tasks_text = (change_dir / "tasks.md").read_text()
    number_for_2_1 = next(n for n, i in task_issues(client).items() if i["title"].startswith("2.1"))
    assert f"- [ ] 2.1 [ISSUE-{number_for_2_1}] POST /refunds endpoint" in tasks_text
    assert "- [x] 1.2 Add Refund entity" in tasks_text
    mapping = json.loads((change_dir / "github.json").read_text())
    assert mapping["repo"] == "acme/shop"
    assert mapping["items"]["2.1"] == number_for_2_1
    assert mapping["epic"] == next(iter(epic_issues(client)))


def test_second_sync_is_idempotent(change_dir):
    client = FakeGitHubClient()
    sync(change_dir, client)
    issue_count = len(client.issues)
    tasks_after_first_sync = (change_dir / "tasks.md").read_text()

    report = sync(change_dir, client)

    assert len(client.issues) == issue_count
    assert report.created_issue_numbers == []
    assert (change_dir / "tasks.md").read_text() == tasks_after_first_sync


def test_new_task_added_later_creates_only_that_ticket(change_dir):
    client = FakeGitHubClient()
    sync(change_dir, client)
    tasks_file = change_dir / "tasks.md"
    tasks_file.write_text(tasks_file.read_text() + "- [ ] 2.3 Email the customer\n")

    report = sync(change_dir, client)

    assert len(report.created_issue_numbers) == 1
    new_issue = client.issues[report.created_issue_numbers[0]]
    assert new_issue["title"] == "2.3 Email the customer"
    assert f"#{report.created_issue_numbers[0]}" in next(iter(epic_issues(client).values()))["body"]


def test_group_by_section_creates_one_ticket_per_section(change_dir):
    client = FakeGitHubClient()

    sync(change_dir, client, group_by="section")

    titles = sorted(issue["title"] for issue in task_issues(client).values())
    assert titles == ["1. Data model", "2. API"]
    api_issue = next(i for i in task_issues(client).values() if i["title"] == "2. API")
    assert "- [ ] 2.1 POST /refunds endpoint" in api_issue["body"]
    assert "## 2. [ISSUE-" in (change_dir / "tasks.md").read_text()


def test_falls_back_to_checklist_when_sub_issues_unsupported(change_dir):
    client = FakeGitHubClient(sub_issues_supported=False)

    report = sync(change_dir, client)

    assert client.sub_issue_links == []
    assert any("sub-issue" in warning for warning in report.warnings)
    assert len(task_issues(client)) == 3


def test_ensures_labels_and_issue_autolink(change_dir):
    client = FakeGitHubClient()

    sync(change_dir, client)

    assert {"epic", "task"} <= client.labels
    assert client.autolinks == ["ISSUE-"]


def test_dry_run_changes_nothing(change_dir):
    client = FakeGitHubClient()
    original_tasks = (change_dir / "tasks.md").read_text()

    report = sync(change_dir, client, dry_run=True)

    assert client.issues == {}
    assert (change_dir / "tasks.md").read_text() == original_tasks
    assert not (change_dir / "github.json").exists()
    assert len(report.planned_titles) == 4  # epic + 3 tasks


def test_missing_tasks_file_is_a_clear_error(tmp_path):
    empty_change = tmp_path / "openspec/changes/empty"
    empty_change.mkdir(parents=True)

    with pytest.raises(github_sync.SyncError, match="tasks.md"):
        sync(empty_change, FakeGitHubClient())


# --- next task -----------------------------------------------------------------------------

def test_next_task_skips_done_closed_and_in_progress_tickets(change_dir):
    client = FakeGitHubClient()
    sync(change_dir, client)
    mapping = json.loads((change_dir / "github.json").read_text())
    issue_1_1, issue_2_1, issue_2_2 = mapping["items"]["1.1"], mapping["items"]["2.1"], mapping["items"]["2.2"]

    assert github_sync.next_task(change_dir, client) == issue_1_1

    client.closed_issue_numbers.add(issue_1_1)
    client.open_pr_titles.append(f"[ISSUE-{issue_2_1}] feat: POST /refunds endpoint")
    assert github_sync.next_task(change_dir, client) == issue_2_2

    client.closed_issue_numbers.add(issue_2_2)
    assert github_sync.next_task(change_dir, client) is None


# --- gh CLI adapter ------------------------------------------------------------------------

def test_gh_cli_client_creates_issue_through_gh_api():
    recorded_commands = []

    def fake_run(command):
        recorded_commands.append(command)
        return json.dumps({"number": 7, "id": 7007})

    client = github_sync.GhCliClient("acme/shop", run=fake_run)
    created = client.create_issue("1.1 Do it", "body", ["task"])

    assert created == github_sync.CreatedIssue(number=7, issue_id=7007)
    command = recorded_commands[0]
    assert command[:3] == ["gh", "api", "repos/acme/shop/issues"]
    assert "title=1.1 Do it" in command and "labels[]=task" in command


# --- v2.1: milestone + label tracking (default; works on free personal accounts) --------------

def test_default_tracking_uses_a_milestone_and_change_label_instead_of_an_epic_issue(change_dir):
    client = FakeGitHubClient()

    report = sync_default(change_dir, client)

    assert epic_issues(client) == {}
    assert len(client.milestones) == 1
    milestone_number, milestone = next(iter(client.milestones.items()))
    assert milestone["title"] == "Add refunds (add-refunds)"
    assert "openspec/changes/add-refunds" in milestone["description"]
    assert report.milestone_number == milestone_number
    for issue in task_issues(client).values():
        assert issue["milestone"] == milestone_number
        assert "change:add-refunds" in issue["labels"]
        assert "Milestone: Add refunds (add-refunds)" in issue["body"]
        assert "Part of #" not in issue["body"]
    assert "change:add-refunds" in client.labels


def test_milestone_sync_is_idempotent_and_recorded_in_mapping(change_dir):
    client = FakeGitHubClient()
    sync_default(change_dir, client)

    report = sync_default(change_dir, client)

    assert len(client.milestones) == 1
    assert report.created_issue_numbers == []
    mapping = json.loads((change_dir / "github.json").read_text())
    assert mapping["tracking"] == "milestone"
    assert mapping["milestone"] == 1
    assert mapping["epic"] is None


def test_tracking_both_creates_milestone_and_parent_issue(change_dir):
    client = FakeGitHubClient()

    sync_default(change_dir, client, tracking="both")

    assert len(client.milestones) == 1 and len(epic_issues(client)) == 1
    epic_number = next(iter(epic_issues(client)))
    for issue in task_issues(client).values():
        assert issue["milestone"] == 1
        assert f"Part of #{epic_number}" in issue["body"]


def test_legacy_mapping_without_tracking_keeps_parent_issue_mode(change_dir):
    client = FakeGitHubClient()
    sync(change_dir, client)  # 2.0-style epic sync
    mapping_file = change_dir / "github.json"
    legacy = json.loads(mapping_file.read_text())
    legacy.pop("tracking", None)
    mapping_file.write_text(json.dumps(legacy))
    (change_dir / "tasks.md").write_text((change_dir / "tasks.md").read_text() + "- [ ] 2.3 Email the customer\n")

    sync_default(change_dir, client)

    assert client.milestones == {}
    new_issue = client.issues[max(client.issues)]
    assert "Part of #" in new_issue["body"]


def test_dry_run_plans_the_milestone(change_dir):
    report = sync_default(change_dir, FakeGitHubClient(), dry_run=True)

    assert report.planned_titles[0] == "Milestone: Add refunds (add-refunds)"
    assert len(report.planned_titles) == 4


def test_gh_cli_client_reuses_existing_milestone_by_title():
    recorded_commands = []

    def fake_run(command):
        recorded_commands.append(command)
        if command[:3] == ["gh", "api", "repos/acme/shop/milestones?state=all&per_page=100"]:
            return json.dumps([{"number": 5, "title": "Add refunds (add-refunds)"}])
        return "{}"

    client = github_sync.GhCliClient("acme/shop", run=fake_run)

    assert client.ensure_milestone("Add refunds (add-refunds)", "desc") == 5
    assert not any("POST" in command for command in recorded_commands[1:2])


def test_gh_cli_client_sets_milestone_on_new_issues():
    recorded_commands = []

    def fake_run(command):
        recorded_commands.append(command)
        return json.dumps({"number": 8, "id": 8008})

    github_sync.GhCliClient("acme/shop", run=fake_run).create_issue("t", "b", ["task"], milestone=5)

    assert "milestone=5" in recorded_commands[0]
