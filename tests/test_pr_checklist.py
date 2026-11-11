"""Behaviour tests for the PR checklist gate shipped to projects (.github/scripts/eng_pr_checklist.py).

A ready (non-draft) PR must link its issue and have every acceptance criterion, Definition-of-Done item and
pending decision checked. Draft PRs only get a report.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/template/.github/scripts/eng_pr_checklist.py"
WORKFLOW = Path(__file__).resolve().parents[1] / "plugins/eng/template/.github/workflows/eng-pr-checklist.yml"
PR_TEMPLATE = Path(__file__).resolve().parents[1] / "plugins/eng/template/.github/pull_request_template.md"

COMPLETE_BODY = """Closes #44
Part of milestone: Add refunds

## Summary
Adds the refunds endpoint.

## Acceptance criteria
- [x] POST /refunds creates a refund — `RefundApiTest#creates refund`
- [x] Refund above order total is rejected with 422 — `RefundApiTest#rejects refund above total`

## Definition of Done
- [x] Tests written first and passing
- [x] Build and lint pass

## Pending decisions
None
"""


def run_check(body: str, title: str = "[ISSUE-44] feat: refunds endpoint", draft: bool = False):
    environment = {**os.environ, "PR_TITLE": title, "PR_BODY": body, "PR_DRAFT": "true" if draft else "false"}
    return subprocess.run([sys.executable, str(SCRIPT)], env=environment, capture_output=True, text=True)


def test_complete_pr_passes():
    result = run_check(COMPLETE_BODY)
    assert result.returncode == 0, result.stdout


def test_unchecked_acceptance_criterion_blocks_and_is_listed():
    body = COMPLETE_BODY.replace("- [x] Refund above", "- [ ] Refund above")
    result = run_check(body)
    assert result.returncode == 1
    assert "Refund above order total is rejected" in result.stdout


def test_unchecked_definition_of_done_item_blocks():
    result = run_check(COMPLETE_BODY.replace("- [x] Build and lint pass", "- [ ] Build and lint pass"))
    assert result.returncode == 1
    assert "Build and lint pass" in result.stdout


def test_open_pending_decision_blocks():
    body = COMPLETE_BODY.replace("## Pending decisions\nNone", "## Pending decisions\n- [ ] Refund partial amounts? (asked PO)")
    result = run_check(body)
    assert result.returncode == 1
    assert "Refund partial amounts?" in result.stdout


def test_resolved_pending_decisions_pass():
    body = COMPLETE_BODY.replace("## Pending decisions\nNone", "## Pending decisions\n- [x] Partial refunds: yes (PO, 2026-11-11)")
    assert run_check(body).returncode == 0


@pytest.mark.parametrize("closing", ["Fixes #44", "resolves #44", "Closed #44"])
def test_accepts_any_closing_keyword(closing):
    assert run_check(COMPLETE_BODY.replace("Closes #44", closing)).returncode == 0


def test_missing_issue_link_blocks():
    result = run_check(COMPLETE_BODY.replace("Closes #44", "Related to #44"))
    assert result.returncode == 1
    assert "Closes #" in result.stdout


def test_no_issue_prs_need_no_link_or_acceptance_criteria():
    body = "## Summary\nBump deps\n\n## Definition of Done\n- [x] Build and tests pass\n"
    assert run_check(body, title="[NO-ISSUE] chore: bump deps").returncode == 0


def test_missing_required_section_blocks():
    body = COMPLETE_BODY.split("## Definition of Done")[0]
    result = run_check(body)
    assert result.returncode == 1
    assert "Definition of Done" in result.stdout


def test_checkboxes_inside_html_comments_are_ignored():
    body = COMPLETE_BODY.replace("## Definition of Done\n", "## Definition of Done\n<!-- - [ ] example hint -->\n")
    assert run_check(body).returncode == 0


def test_draft_prs_only_report_pending_items():
    result = run_check(COMPLETE_BODY.replace("- [x] Build and lint pass", "- [ ] Build and lint pass"), draft=True)
    assert result.returncode == 0
    assert "Build and lint pass" in result.stdout


def test_workflow_passes_pr_data_via_env_and_reruns_when_marked_ready():
    workflow = WORKFLOW.read_text()
    assert "PR_BODY: ${{ github.event.pull_request.body }}" in workflow
    assert "ready_for_review" in workflow and "edited" in workflow
    run_steps = workflow.split("run:", 1)[1]
    assert "${{" not in run_steps  # no expression interpolation inside shell steps


def test_pr_template_has_the_required_sections():
    template = PR_TEMPLATE.read_text()
    for section in ("## Acceptance criteria", "## Definition of Done", "## Pending decisions", "Closes #"):
        assert section in template
