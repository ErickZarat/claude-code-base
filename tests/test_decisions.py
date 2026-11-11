"""Behaviour tests for decisions.py — lightweight decision records in docs/decisions/."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/decisions.py"


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, check=True).stdout


def test_new_decision_gets_next_number_slug_and_template(tmp_path):
    first = run(tmp_path, "new", "--title", "Use ClickHouse for refund analytics", "--change", "add-refunds").strip()
    second = run(tmp_path, "new", "--title", "Paginate with keyset cursors").strip()

    assert first == "docs/decisions/0001-use-clickhouse-for-refund-analytics.md"
    assert second == "docs/decisions/0002-paginate-with-keyset-cursors.md"
    text = (tmp_path / first).read_text()
    for section in ("# 0001. Use ClickHouse for refund analytics", "Status: Proposed", "## Context",
                    "## Options considered", "## Decision", "## Consequences", "openspec/changes/add-refunds"):
        assert section in text


def test_supersedes_marks_the_old_decision(tmp_path):
    old = run(tmp_path, "new", "--title", "Offset pagination").strip()
    new = run(tmp_path, "new", "--title", "Keyset pagination", "--supersedes", "1").strip()

    assert "Supersedes: [0001]" in (tmp_path / new).read_text()
    assert "Status: Superseded by [0002]" in (tmp_path / old).read_text()


def test_list_shows_number_status_and_title(tmp_path):
    run(tmp_path, "new", "--title", "Offset pagination")
    run(tmp_path, "new", "--title", "Keyset pagination", "--supersedes", "1")

    listing = run(tmp_path, "list")

    assert "0001  Superseded by [0002]" in listing and "Offset pagination" in listing
    assert "0002  Proposed" in listing
