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

    def __init__(self, sub_issues_supported: bool = True, dependencies_supported: bool = True):
        self.issues: dict[int, dict] = {}
        self.sub_issue_links: list[tuple[int, int]] = []
        self.labels: set[str] = set()
        self.autolinks: list[str] = []
        self.sub_issues_supported = sub_issues_supported
        self.open_pr_titles: list[str] = []
        self.closed_issue_numbers: set[int] = set()
        self.milestones: dict[int, dict] = {}
        self.dependencies_supported = dependencies_supported
        self.open_prs: list[dict] = []  # {"number", "title", "author", "draft"}
        self.login = "me"

    def create_issue(self, title, body, labels, milestone=None):
        number = len(self.issues) + 100
        self.issues[number] = {"title": title, "body": body, "labels": list(labels), "milestone": milestone,
                               "assignees": [], "blocked_by": []}
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
        if key_prefix not in self.autolinks:
            self.autolinks.append(key_prefix)
        return True

    def open_pull_request_titles(self):
        return list(self.open_pr_titles) + [pr["title"] for pr in self.open_prs]

    def open_pull_requests(self):
        return [dict(pr) for pr in self.open_prs] + [{"number": 0, "title": title, "author": "?", "draft": False}
                                                     for title in self.open_pr_titles]

    def issue_body(self, number):
        return self.issues[number]["body"]

    def add_blocked_by(self, number, blocking_issue_id):
        if not self.dependencies_supported:
            return False
        blocking = blocking_issue_id // 1000
        if blocking not in self.issues[number]["blocked_by"]:
            self.issues[number]["blocked_by"].append(blocking)
        return True

    def blocked_by(self, number):
        return list(self.issues[number]["blocked_by"])

    def issue_id(self, number):
        return number * 1000

    def assignees(self, number):
        return list(self.issues[number]["assignees"])

    def add_assignee(self, number, login):
        self.issues[number]["assignees"].append(login)

    def current_login(self):
        return self.login

    def is_issue_open(self, number):
        return number not in self.closed_issue_numbers

    def issue_type_and_labels(self, number):
        issue = self.issues[number]
        return issue.get("type"), issue["labels"]


@pytest.fixture
def change_dir(tmp_path):
    directory = tmp_path / "openspec/changes/add-refunds"
    directory.mkdir(parents=True)
    (directory / "proposal.md").write_text("# Add refunds\n\n## Why\nCustomers need refunds.\n")
    (directory / "tasks.md").write_text(TASKS_MD)
    return directory


def sync(change_dir, client, **options):
    """Parent-issue mode (tracking="epic"), one ticket per task — the behaviour most tests below cover."""
    options.setdefault("tracking", "epic")
    options.setdefault("group_by", "task")
    return github_sync.sync_change(change_dir, client, repo="acme/shop", **options)


def sync_default(change_dir, client, **options):
    """Default tracking (milestone), one ticket per task."""
    options.setdefault("group_by", "task")
    return github_sync.sync_change(change_dir, client, repo="acme/shop", **options)


def task_issues(client):
    return {number: issue for number, issue in client.issues.items() if "task" in issue["labels"]}


def epic_issues(client):
    return {number: issue for number, issue in client.issues.items() if "epic" in issue["labels"]}


# --- tag / branch / title helpers ---------------------------------------------------------

def test_issue_tag_branch_and_pr_title_formats():
    assert github_sync.issue_tag(43) == "[ISSUE-43]"
    assert github_sync.issue_tag(10, "BUG") == "[BUG-10]"
    assert github_sync.branch_name(43, "POST /refunds endpoint!") == "issue-43-post-refunds-endpoint"
    assert github_sync.branch_name(10, "Null total crashes", "BUG") == "bug-10-null-total-crashes"
    assert len(github_sync.branch_name(43, "word " * 40)) <= 60
    assert github_sync.pr_title(43, "feat", "POST /refunds endpoint") == "[ISSUE-43] feat: POST /refunds endpoint"
    assert github_sync.pr_title(7, "feat", "Refunds", "FEATURE") == "[FEATURE-7] feat: Refunds"


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
    assert f"- [ ] 2.1 [TASK-{number_for_2_1}] POST /refunds endpoint" in tasks_text
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
    assert "## 2. [TASK-" in (change_dir / "tasks.md").read_text()


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
    assert {"ISSUE-", "TASK-", "BUG-", "FEATURE-", "STORY-"} <= set(client.autolinks)


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
    client.open_pr_titles.append(f"[TASK-{issue_2_1}] feat: POST /refunds endpoint")
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


# --- v2.7: tag prefix from the issue type ------------------------------------------------------

@pytest.mark.parametrize(
    "issue_type, labels, expected",
    [
        ("Bug", [], "BUG"),
        ("Feature", ["task"], "FEATURE"),        # native type wins over labels
        ("User Story", [], "STORY"),
        ("Spike", [], "SPIKE"),
        (None, ["bug", "task"], "BUG"),          # bug label wins over task
        (None, ["enhancement"], "FEATURE"),
        (None, ["Feature"], "FEATURE"),
        (None, ["task", "change:add-refunds"], "TASK"),
        (None, ["story"], "STORY"),
        (None, ["chore"], "CHORE"),
        (None, ["good first issue", "help wanted"], "ISSUE"),
        (None, [], "ISSUE"),
    ],
)
def test_tag_kind_comes_from_issue_type_then_labels_then_default(issue_type, labels, expected):
    assert github_sync.tag_kind(issue_type, labels) == expected


def test_tag_for_issue_looks_the_kind_up_on_github(change_dir):
    client = FakeGitHubClient()
    bug = client.create_issue("Null total crashes", "", ["bug"]).number
    plain = client.create_issue("Something", "", []).number

    assert github_sync.tag_for_issue(client, bug) == "[BUG-%d]" % bug
    assert github_sync.tag_for_issue(client, plain) == "[ISSUE-%d]" % plain


def test_legacy_issue_tags_in_tasks_md_are_still_recognised(change_dir):
    tasks = change_dir / "tasks.md"
    tasks.write_text(tasks.read_text().replace("- [ ] 1.1 Add refunds", "- [ ] 1.1 [ISSUE-500] Add refunds"))
    client = FakeGitHubClient()

    sync(change_dir, client)

    assert not any(issue["title"].startswith("1.1") for issue in task_issues(client).values())
    assert "[ISSUE-500] Add refunds" in tasks.read_text()
    assert json.loads((change_dir / "github.json").read_text())["items"]["1.1"] == 500


def test_next_task_sees_open_prs_with_any_kind_prefix(change_dir):
    client = FakeGitHubClient()
    sync(change_dir, client)
    first = json.loads((change_dir / "github.json").read_text())["items"]["1.1"]
    client.open_pr_titles.append(f"[BUG-{first}] fix: migration")

    assert github_sync.next_task(change_dir, client) != first


def test_gh_cli_client_reads_native_type_and_labels():
    def fake_run(command):
        return json.dumps({"state": "open", "type": {"name": "Bug"}, "labels": [{"name": "task"}]})

    client = github_sync.GhCliClient("acme/shop", run=fake_run)

    assert client.issue_type_and_labels(10) == ("Bug", ["task"])


def test_gh_cli_client_handles_repos_without_issue_types():
    client = github_sync.GhCliClient("acme/shop", run=lambda command: json.dumps({"labels": [{"name": "bug"}]}))

    assert client.issue_type_and_labels(10) == (None, ["bug"])


# --- v2.8: task dependencies and size ------------------------------------------------------------

DEPENDENT_TASKS = """## 1. Refunds
- [ ] 1.1 Add refunds table migration (size: S)
- [ ] 1.2 POST /refunds endpoint (after: 1.1; size: M)
- [ ] 1.3 Reject refunds above total (after: 1.2)
"""


def test_annotations_become_dependencies_and_size_labels_not_title_text(change_dir):
    (change_dir / "tasks.md").write_text(DEPENDENT_TASKS)
    client = FakeGitHubClient()

    sync(change_dir, client)

    mapping = json.loads((change_dir / "github.json").read_text())["items"]
    endpoint = client.issues[mapping["1.2"]]
    assert endpoint["title"] == "1.2 POST /refunds endpoint"
    assert "size:M" in endpoint["labels"] and "size:S" in client.issues[mapping["1.1"]]["labels"]
    assert f"Depends on #{mapping['1.1']}" in endpoint["body"]
    assert {"size:S", "size:M"} <= client.labels
    assert "(after: 1.1; size: M)" in (change_dir / "tasks.md").read_text()  # annotation kept in tasks.md


def test_next_task_waits_for_dependencies(change_dir):
    (change_dir / "tasks.md").write_text(DEPENDENT_TASKS)
    client = FakeGitHubClient()
    sync(change_dir, client)
    mapping = json.loads((change_dir / "github.json").read_text())["items"]

    assert github_sync.next_task(change_dir, client) == mapping["1.1"]

    client.open_pr_titles.append(f"[TASK-{mapping['1.1']}] feat: migration")  # 1.1 in progress, not merged
    assert github_sync.next_task(change_dir, client) is None  # 1.2 is blocked by 1.1

    client.open_pr_titles.clear()
    client.closed_issue_numbers.add(mapping["1.1"])  # 1.1 merged → issue closed
    assert github_sync.next_task(change_dir, client) == mapping["1.2"]


def test_blocked_tasks_are_explained(change_dir):
    (change_dir / "tasks.md").write_text(DEPENDENT_TASKS)
    client = FakeGitHubClient()
    sync(change_dir, client)
    mapping = json.loads((change_dir / "github.json").read_text())["items"]
    client.open_pr_titles.append(f"[TASK-{mapping['1.1']}] feat: migration")

    blocked = github_sync.blocked_tasks(change_dir, client)

    assert blocked == {mapping["1.2"]: [mapping["1.1"]], mapping["1.3"]: [mapping["1.2"]]}


# --- v2.9: team coordination ---------------------------------------------------------------------

def synced_dependent_change(change_dir, client=None):
    (change_dir / "tasks.md").write_text(DEPENDENT_TASKS)
    client = client or FakeGitHubClient()
    sync(change_dir, client)
    return client, json.loads((change_dir / "github.json").read_text())["items"]


def test_sync_creates_native_blocked_by_links(change_dir):
    client, items = synced_dependent_change(change_dir)

    assert client.blocked_by(items["1.2"]) == [items["1.1"]]
    assert client.blocked_by(items["1.3"]) == [items["1.2"]]


def test_native_dependency_failure_falls_back_to_body_text_with_warning(change_dir):
    (change_dir / "tasks.md").write_text(DEPENDENT_TASKS)
    client = FakeGitHubClient(dependencies_supported=False)

    report = sync(change_dir, client)

    items = json.loads((change_dir / "github.json").read_text())["items"]
    assert f"Depends on #{items['1.1']}" in client.issue_body(items["1.2"])
    assert any("blocked-by" in warning for warning in report.warnings)


def test_resync_adds_dependencies_planned_later(change_dir):
    client, items = synced_dependent_change(change_dir)
    tasks = change_dir / "tasks.md"
    tasks.write_text(tasks.read_text().replace("1.1 [TASK-%d] Add refunds table migration (size: S)" % items["1.1"],
                                               "1.1 [TASK-%d] Add refunds table migration (size: S)" % items["1.1"])
                     + "- [ ] 1.4 Refund emails (after: 1.1, 1.3)\n")
    tasks.write_text(tasks.read_text().replace("Reject refunds above total (after: 1.2)", "Reject refunds above total (after: 1.1, 1.2)"))

    sync(change_dir, client)

    items = json.loads((change_dir / "github.json").read_text())["items"]
    assert sorted(client.blocked_by(items["1.3"])) == sorted([items["1.1"], items["1.2"]])
    assert f"Depends on #{items['1.1']}" in client.issue_body(items["1.3"])
    assert sorted(client.blocked_by(items["1.4"])) == sorted([items["1.1"], items["1.3"]])


def test_dependency_discovered_later_is_recorded_on_github_only(change_dir):
    client, items = synced_dependent_change(change_dir)
    client.closed_issue_numbers.update({items["1.1"]})
    tasks_before = (change_dir / "tasks.md").read_text()

    github_sync.block(client, items["1.2"], by=items["1.3"])

    assert items["1.3"] in client.blocked_by(items["1.2"])
    assert f"Depends on #{items['1.3']}" in client.issue_body(items["1.2"])
    assert (change_dir / "tasks.md").read_text() == tasks_before
    assert github_sync.next_task(change_dir, client) is None  # 1.2 now waits for 1.3, which waits for 1.2's... 1.3 blocked
    assert items["1.2"] in github_sync.blocked_tasks(change_dir, client)


def test_claim_assigns_me_and_refuses_someone_elses_ticket(change_dir):
    client, items = synced_dependent_change(change_dir)

    github_sync.claim(client, items["1.1"])
    assert client.assignees(items["1.1"]) == ["me"]

    client.add_assignee(items["1.2"], "dev-b")
    with pytest.raises(github_sync.ClaimError, match="dev-b"):
        github_sync.claim(client, items["1.2"])
    github_sync.claim(client, items["1.2"], force=True)
    assert "me" in client.assignees(items["1.2"])


def test_next_skips_tickets_claimed_by_others_and_resumes_mine_first():
    tasks = """## 1. Lanes
- [ ] 1.1 Lane one first step
- [ ] 1.2 Lane two first step
- [ ] 1.3 Lane two second step
"""
    import tempfile
    directory = Path(tempfile.mkdtemp()) / "openspec/changes/lanes"
    directory.mkdir(parents=True)
    (directory / "tasks.md").write_text(tasks)
    client = FakeGitHubClient()
    sync(directory, client)
    items = json.loads((directory / "github.json").read_text())["items"]

    client.add_assignee(items["1.1"], "dev-b")
    assert github_sync.next_task(directory, client) == items["1.2"]

    client.add_assignee(items["1.3"], "me")
    assert github_sync.next_task(directory, client) == items["1.3"]  # resume my own work first


def test_status_board_shows_who_is_on_what(change_dir):
    client, items = synced_dependent_change(change_dir)
    client.add_assignee(items["1.1"], "dev-b")
    client.open_prs.append({"number": 7, "title": f"[TASK-{items['1.1']}] feat: migration", "author": "dev-b", "draft": False})

    rows = {row.issue_number: row for row in github_sync.status(change_dir, client)}

    assert rows[items["1.1"]].state == "in review" and rows[items["1.1"]].who == "dev-b" and rows[items["1.1"]].pull_request == 7
    assert rows[items["1.2"]].state == "blocked" and rows[items["1.2"]].waiting_for == [items["1.1"]]

    client.open_prs.clear()
    client.closed_issue_numbers.add(items["1.1"])
    rows = {row.issue_number: row for row in github_sync.status(change_dir, client)}
    assert rows[items["1.1"]].state == "done"
    assert rows[items["1.2"]].state == "ready"


def test_draft_pr_or_assignee_means_in_progress(change_dir):
    client, items = synced_dependent_change(change_dir)
    client.add_assignee(items["1.1"], "dev-b")
    rows = {row.issue_number: row for row in github_sync.status(change_dir, client)}
    assert rows[items["1.1"]].state == "in progress"


def test_sync_ticks_tasks_whose_ticket_is_closed(change_dir):
    client, items = synced_dependent_change(change_dir)
    client.closed_issue_numbers.add(items["1.1"])

    sync(change_dir, client)

    text = (change_dir / "tasks.md").read_text()
    assert f"- [x] 1.1 [TASK-{items['1.1']}]" in text
    assert f"- [ ] 1.2 [TASK-{items['1.2']}]" in text


def test_gh_cli_client_maps_open_pull_requests():
    payload = json.dumps([{"number": 7, "title": "[TASK-1] feat: x", "author": {"login": "dev-b"}, "isDraft": True}])
    client = github_sync.GhCliClient("acme/shop", run=lambda command: payload)
    assert client.open_pull_requests() == [{"number": 7, "title": "[TASK-1] feat: x", "author": "dev-b", "draft": True}]


def test_gh_cli_client_treats_unavailable_dependencies_as_none():
    import subprocess as sp

    def failing_run(command):
        raise sp.CalledProcessError(1, command)

    client = github_sync.GhCliClient("acme/shop", run=failing_run)
    assert client.blocked_by(3) == [] and client.add_blocked_by(3, 4000) is False


# --- v3.0: one PR per section is the default -------------------------------------------------------

SECTION_TASKS = """## 1. Data model
- [ ] 1.1 Add refunds table migration
- [ ] 1.2 Add Refund entity (after: 1.1)

## 2. API
- [ ] 2.1 POST /refunds endpoint (after: 1.2)
- [ ] 2.2 Reject refunds above the order total (after: 2.1)

## 3. Emails
- [ ] 3.1 Refund confirmation template
"""


def test_default_is_one_ticket_per_section(change_dir):
    (change_dir / "tasks.md").write_text(SECTION_TASKS)
    client = FakeGitHubClient()

    github_sync.sync_change(change_dir, client, repo="acme/shop")

    titles = sorted(issue["title"] for issue in task_issues(client).values())
    assert titles == ["1. Data model", "2. API", "3. Emails"]
    assert json.loads((change_dir / "github.json").read_text())["group_by"] == "section"


def test_section_dependencies_come_from_task_dependencies_across_sections(change_dir):
    (change_dir / "tasks.md").write_text(SECTION_TASKS)
    client = FakeGitHubClient()

    github_sync.sync_change(change_dir, client, repo="acme/shop")

    items = json.loads((change_dir / "github.json").read_text())["items"]
    assert client.blocked_by(items["2"]) == [items["1"]]   # 2.1 after 1.2 → section 2 after section 1
    assert client.blocked_by(items["1"]) == []             # 1.2 after 1.1 is inside the section
    assert client.blocked_by(items["3"]) == []
    assert github_sync.next_task(change_dir, client) == items["1"]
    client.add_assignee(items["1"], "dev-b")
    assert github_sync.next_task(change_dir, client) == items["3"]  # 2 is blocked by 1, 3 is free


def test_existing_task_mode_changes_keep_their_granularity(change_dir):
    client = FakeGitHubClient()
    sync(change_dir, client)  # task mode
    mapping_file = change_dir / "github.json"
    legacy = json.loads(mapping_file.read_text())
    legacy.pop("group_by")
    mapping_file.write_text(json.dumps(legacy))
    (change_dir / "tasks.md").write_text((change_dir / "tasks.md").read_text() + "- [ ] 2.3 Email the customer\n")

    report = github_sync.sync_change(change_dir, client, repo="acme/shop", tracking="epic")

    assert client.issues[report.created_issue_numbers[0]]["title"] == "2.3 Email the customer"


def test_closed_section_ticket_ticks_all_its_tasks(change_dir):
    (change_dir / "tasks.md").write_text(SECTION_TASKS)
    client = FakeGitHubClient()
    github_sync.sync_change(change_dir, client, repo="acme/shop")
    items = json.loads((change_dir / "github.json").read_text())["items"]
    client.closed_issue_numbers.add(items["1"])

    github_sync.sync_change(change_dir, client, repo="acme/shop")

    text = (change_dir / "tasks.md").read_text()
    assert "- [x] 1.1 Add refunds table migration" in text and "- [x] 1.2 Add Refund entity" in text
    assert "- [ ] 2.1 POST /refunds endpoint" in text
