"""Behaviour tests for findings_report.py — recurring review findings across ledgers (the learning loop)."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/findings_report.py"
HEADER = "| ID | Fingerprint | Area | Location | Finding | Seen | Status | Resolution |\n|---|---|---|---|---|---|---|---|\n"


def ledger(root: Path, relative: str, rows: list[str]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Review ledger\n\n## Round 1\n" + HEADER + "\n".join(rows) + "\n")


def row(finding_id, fingerprint, area="perf", status="VERIFIED"):
    return f"| {finding_id} | {fingerprint} | {area} | X.kt:1 | something | 1 | {status} | fixed |"


def run(root, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True, check=True).stdout


def test_recurring_problem_classes_across_ledgers_are_reported(tmp_path):
    ledger(tmp_path, ".reviews/task-1-a/ledger.md", [row("R1-MAJ-1", "RefundRepo · N+1 query"),
                                                     row("R1-MIN-2", "Foo · unclear name", "quality")])
    ledger(tmp_path, ".reviews/task-2-b/ledger.md", [row("R1-MAJ-1", "OrderRepo · N+1 query")])
    ledger(tmp_path, "openspec/changes/archive/2026-11-01-x/reviews/task-3-c/ledger.md",
           [row("R2-BLK-4", "UserRepo · n+1 Query")])

    report = run(tmp_path)

    recurring = report.split("Recurring")[1]
    assert "n+1 query" in recurring and "3 findings in 3 ledgers" in recurring
    assert "unclear name" not in recurring


def test_totals_by_severity_and_area(tmp_path):
    ledger(tmp_path, ".reviews/a/ledger.md", [row("R1-MAJ-1", "A · x"), row("R1-BLK-2", "B · y", "security"),
                                             row("R1-Q-3", "C · z", "requirements")])
    report = run(tmp_path)
    assert "BLK 1" in report and "MAJ 1" in report and "Q 1" in report
    assert "security 1" in report


def test_superseded_rows_are_not_double_counted(tmp_path):
    ledger(tmp_path, ".reviews/a/ledger.md", [row("R1-Q-1", "Repo · unbounded query", status="SUPERSEDED → R2-MAJ-2"),
                                             row("R2-MAJ-2", "Repo · unbounded query")])
    assert "MAJ 1" in run(tmp_path) and "Q 1" not in run(tmp_path)


def test_threshold_is_configurable(tmp_path):
    ledger(tmp_path, ".reviews/a/ledger.md", [row("R1-MAJ-1", "A · missing timeout")])
    ledger(tmp_path, ".reviews/b/ledger.md", [row("R1-MAJ-1", "B · missing timeout")])
    assert "missing timeout" not in run(tmp_path).split("Recurring")[1]
    assert "missing timeout" in run(tmp_path, "--min", "2").split("Recurring")[1]


# --- v2.10: metrics to see whether development gets it right the first time ---------------------

def write_ledger(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_reports_rounds_and_findings_per_100_changed_lines(tmp_path):
    write_ledger(tmp_path, ".reviews/task-1/ledger.md",
                 "## Round 1 — 2026-11-11 — scope: FULL — changed lines: 200 — verdict: REQUEST CHANGES\n" + HEADER
                 + row("R1-MAJ-1", "A · x") + "\n" + row("R1-MIN-2", "B · y", "quality") + "\n"
                 + "## Round 2 — 2026-11-11 — scope: VERIFY — changed lines: 20 — verdict: APPROVE\n" + HEADER
                 + row("R2-MIN-3", "C · z", "quality") + "\n")
    write_ledger(tmp_path, ".reviews/task-2/ledger.md",
                 "## Round 1 — 2026-11-12 — scope: FULL — changed lines: 100 — verdict: APPROVE\n" + HEADER)

    report = run(tmp_path)

    assert "PRs reviewed: 2" in report
    assert "average rounds per PR: 1.5" in report
    assert "first-round findings per 100 changed lines: 0.7" in report  # 2 findings / 300 lines
    assert "clean first round: 1 of 2" in report


def test_ledgers_without_line_counts_still_report_rounds(tmp_path):
    ledger(tmp_path, ".reviews/a/ledger.md", [row("R1-MAJ-1", "A · x")])
    report = run(tmp_path)
    assert "PRs reviewed: 1" in report and "per 100 changed lines: n/a" in report
