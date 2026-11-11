"""The PR-title check shipped to projects must enforce the [ISSUE-n] prefix without shell injection."""

import re
import subprocess
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[1] / "plugins/eng/template/.github/workflows/eng-pr-title.yml"


def title_check_script() -> str:
    text = WORKFLOW.read_text()
    return text.split("run: |", 1)[1]


def run_check(title: str) -> int:
    script = "\n".join(line[10:] for line in title_check_script().splitlines() if line.strip())
    return subprocess.run(["bash", "-c", script], env={"PR_TITLE": title, "PATH": "/usr/bin:/bin"},
                          capture_output=True, text=True).returncode


def test_title_is_passed_through_env_not_interpolated_into_the_script():
    assert "${{ github.event.pull_request.title }}" not in title_check_script()
    assert "PR_TITLE: ${{ github.event.pull_request.title }}" in WORKFLOW.read_text()


@pytest.mark.parametrize("title", ["[ISSUE-43] feat: refunds endpoint", "[ISSUE-7] fix(api): null total", "[NO-ISSUE] chore: bump deps"])
def test_accepts_tagged_titles(title):
    assert run_check(title) == 0


@pytest.mark.parametrize("title", ["feat: refunds", "ISSUE-43 feat: x", "[ISSUE-] feat", "[issue-43] feat: x", "[ISSUE-43]feat: x"])
def test_rejects_untagged_titles(title):
    assert run_check(title) != 0
