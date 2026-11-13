"""Behaviour tests for fix_brief_check.py — a BLOCKER/MAJOR fix must show its root cause, sweep and failing test."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/fix_brief_check.py"
HEADER = "| ID | Fingerprint | Area | Location | Finding | Seen | Status | Resolution |\n|---|---|---|---|---|---|---|---|\n"

COMPLETE_BRIEF = """#### {id}
- Fails when: refund amount 0 → 201 Created; expected 422
- Root cause: amount is validated in the controller only, so the queue consumer path never checks it
- Same class elsewhere: RefundConsumer.kt:40 (fixed), searched `amount` in refunds module
- Fix site: Money value object rejects non-positive amounts in its constructor
- Tests: `rejects zero refund` (failed first: yes), `consumer rejects zero refund` (failed first: yes)
"""


def row(finding_id, status="FIXED (self-verified)", seen=1):
    return f"| {finding_id} | RefundService · input validation | quality | X.kt:1 | zero refund accepted | {seen} | {status} | abc123 |"


def write_ledger(tmp_path, rounds: list[list[str]], briefs: str = "") -> Path:
    text = "# Review ledger\n\n"
    for number, rows in enumerate(rounds, start=1):
        text += f"## Round {number} — 2026-11-13 — scope: FULL — verdict: REQUEST CHANGES\n" + HEADER + "\n".join(rows) + "\n\n"
    if briefs:
        text += "## Fix briefs\n\n" + briefs
    path = tmp_path / "ledger.md"
    path.write_text(text)
    return path


def run(ledger):
    return subprocess.run([sys.executable, str(SCRIPT), str(ledger)], capture_output=True, text=True)


def test_fixed_major_with_complete_brief_passes(tmp_path):
    ledger = write_ledger(tmp_path, [[row("R1-MAJ-1")]], COMPLETE_BRIEF.format(id="R1-MAJ-1"))
    result = run(ledger)
    assert result.returncode == 0, result.stdout
    assert "1 BLOCKER/MAJOR fix" in result.stdout


def test_fixed_blocker_without_brief_fails(tmp_path):
    result = run(write_ledger(tmp_path, [[row("R1-BLK-1")]]))
    assert result.returncode == 1
    assert "R1-BLK-1: no fix brief" in result.stdout


def test_missing_fields_are_named(tmp_path):
    brief = "#### R1-MAJ-1\n- Fails when: zero refund accepted\n- Tests: `rejects zero refund` (failed first: yes)\n"
    result = run(write_ledger(tmp_path, [[row("R1-MAJ-1")]], brief))
    assert result.returncode == 1
    for field in ("Root cause", "Same class elsewhere", "Fix site"):
        assert f"R1-MAJ-1: missing '{field}'" in result.stdout


def test_test_must_have_failed_before_the_fix(tmp_path):
    brief = COMPLETE_BRIEF.format(id="R1-MAJ-1").replace("failed first: yes", "failed first: no")
    result = run(write_ledger(tmp_path, [[row("R1-MAJ-1")]], brief))
    assert result.returncode == 1
    assert "R1-MAJ-1: no test shown failing before the fix" in result.stdout


def test_minors_and_open_findings_need_no_brief(tmp_path):
    rows = [row("R1-MIN-1"), row("R1-MAJ-2", status="OPEN"), row("R1-MAJ-3", status="DECLINED (user)")]
    assert run(write_ledger(tmp_path, [rows])).returncode == 0


def test_recurring_finding_must_explain_why_the_previous_fix_missed(tmp_path):
    rounds = [[row("R1-MAJ-1", status="REOPENED")], [row("R1-MAJ-1", status="FIXED (author)", seen=2)]]
    result = run(write_ledger(tmp_path, rounds, COMPLETE_BRIEF.format(id="R1-MAJ-1")))
    assert result.returncode == 1
    assert "R1-MAJ-1: seen 2 times — missing 'Previous fix missed'" in result.stdout

    brief = COMPLETE_BRIEF.format(id="R1-MAJ-1") + "- Previous fix missed: patched the controller, not the consumer path\n"
    assert run(write_ledger(tmp_path, rounds, brief)).returncode == 0


def test_latest_status_wins(tmp_path):
    # Fixed in round 1, reopened in round 2 and still open: no brief required yet.
    rounds = [[row("R1-MAJ-1")], [row("R1-MAJ-1", status="REOPENED", seen=2)]]
    assert run(write_ledger(tmp_path, rounds)).returncode == 0
