"""Behaviour tests for spec_lint.py — is an OpenSpec change ready to implement?"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/spec_lint.py"

GOOD_SPEC = """# Delta for billing

## ADDED Requirements

### Requirement: Refund creation
The system SHALL create a refund for a paid order.

#### Scenario: Valid refund is created
- **WHEN** a customer requests a refund for a paid order
- **THEN** a refund is created with status PENDING

#### Scenario: Refund above total is rejected
- **WHEN** the requested amount exceeds the order total
- **THEN** the request fails with 422

## REMOVED Requirements

### Requirement: Manual refunds
**Reason**: replaced by refund creation
"""

GOOD_TASKS = """## 1. Refunds
- [ ] 1.1 Add refund creation endpoint (size: M)
- [ ] 1.2 Reject refund above order total (after: 1.1; size: S)
"""

GOOD_DESIGN = """# Design

## Non-functional requirements
| Aspect | Target |
|---|---|
| Latency | p95 < 200 ms |
"""


def make_change(tmp_path, spec=GOOD_SPEC, tasks=GOOD_TASKS, design=GOOD_DESIGN, proposal="# Add refunds\n"):
    change = tmp_path / "openspec/changes/add-refunds"
    (change / "specs/billing").mkdir(parents=True)
    (change / "proposal.md").write_text(proposal)
    if spec is not None:
        (change / "specs/billing/spec.md").write_text(spec)
    if tasks is not None:
        (change / "tasks.md").write_text(tasks)
    if design is not None:
        (change / "design.md").write_text(design)
    return change


def lint(change, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--change", str(change), *args],
                          capture_output=True, text=True)


def test_ready_change_passes_cleanly(tmp_path):
    result = lint(make_change(tmp_path))
    assert result.returncode == 0, result.stdout
    assert "ERROR" not in result.stdout and "WARN" not in result.stdout


def test_requirement_without_scenarios_is_an_error(tmp_path):
    spec = GOOD_SPEC.replace("## REMOVED", "### Requirement: Refund emails\nThe system SHALL email.\n\n## REMOVED")
    result = lint(make_change(tmp_path, spec=spec))
    assert result.returncode == 1
    assert "ERROR" in result.stdout and "Refund emails" in result.stdout and "no scenarios" in result.stdout


def test_removed_requirements_need_no_scenarios(tmp_path):
    assert "Manual refunds" not in lint(make_change(tmp_path)).stdout


def test_scenario_missing_then_is_an_error(tmp_path):
    spec = GOOD_SPEC.replace("- **THEN** a refund is created with status PENDING\n", "")
    result = lint(make_change(tmp_path, spec=spec))
    assert result.returncode == 1
    assert "Valid refund is created" in result.stdout and "THEN" in result.stdout


def test_vague_words_are_warned_with_location(tmp_path):
    spec = GOOD_SPEC.replace("a refund is created with status PENDING", "the refund is created quickly and properly")
    result = lint(make_change(tmp_path, spec=spec))
    assert result.returncode == 0
    assert "WARN" in result.stdout and "quickly" in result.stdout and "spec.md:" in result.stdout


def test_change_without_error_scenarios_is_warned(tmp_path):
    spec = GOOD_SPEC.replace("#### Scenario: Refund above total is rejected\n- **WHEN** the requested amount exceeds the order total\n- **THEN** the request fails with 422\n", "")
    result = lint(make_change(tmp_path, spec=spec))
    assert "error or edge-case scenario" in result.stdout


def test_requirement_not_mentioned_by_any_task_is_warned(tmp_path):
    tasks = "## 1. Misc\n- [ ] 1.1 Update the README\n"
    result = lint(make_change(tmp_path, tasks=tasks))
    assert "Refund creation" in result.stdout and "no task" in result.stdout


def test_missing_specs_or_tasks_are_errors(tmp_path):
    assert lint(make_change(tmp_path, spec=None)).returncode == 1
    result = lint(make_change(tmp_path / "other", tasks=None))
    assert result.returncode == 1 and "tasks.md" in result.stdout


def test_missing_non_functional_section_is_warned(tmp_path):
    result = lint(make_change(tmp_path, design="# Design\nUse a table.\n"))
    assert "Non-functional requirements" in result.stdout


def test_nfr_section_may_live_in_the_proposal(tmp_path):
    result = lint(make_change(tmp_path, design=None, proposal="# Add refunds\n\n## Non-functional requirements\nNone beyond defaults.\n"))
    assert "Non-functional" not in result.stdout


def test_task_dependency_problems_are_errors(tmp_path):
    tasks = "## 1. Refunds\n- [ ] 1.1 Refund creation (after: 1.2)\n- [ ] 1.2 Refund creation part two (after: 1.1)\n- [ ] 1.3 Refund creation extra (after: 9.9)\n"
    result = lint(make_change(tmp_path, tasks=tasks))
    assert result.returncode == 1
    assert "9.9" in result.stdout and "cycle" in result.stdout


def test_large_tasks_are_warned(tmp_path):
    tasks = GOOD_TASKS.replace("(size: M)", "(size: L)")
    assert "split" in lint(make_change(tmp_path, tasks=tasks)).stdout


def test_strict_mode_fails_on_warnings(tmp_path):
    spec = GOOD_SPEC.replace("status PENDING", "status PENDING as needed")
    assert lint(make_change(tmp_path, spec=spec), "--strict").returncode == 1


# --- v2.9: plan view for parallel work ------------------------------------------------------------

LANES_TASKS = """## 1. Refunds
- [ ] 1.1 Refund creation table (size: S)
- [ ] 1.2 Refund creation endpoint (after: 1.1)
- [ ] 1.3 Reject refund above total (after: 1.2)
## 2. Emails
- [ ] 2.1 Refund creation email template
- [ ] 2.2 Send refund creation email (after: 2.1, 1.2)
"""


def test_plan_shows_levels_critical_path_and_parallel_capacity(tmp_path):
    output = lint(make_change(tmp_path, tasks=LANES_TASKS)).stdout

    assert "Plan" in output
    assert "level 1: 1.1, 2.1" in output
    assert "level 2: 1.2" in output
    assert "level 3: 1.3, 2.2" in output
    assert "critical path: 1.1 → 1.2 → 1.3" in output or "critical path: 1.1 → 1.2 → 2.2" in output
    assert "max parallel: 2" in output
    assert "single chain" not in output


def test_single_chain_is_warned(tmp_path):
    tasks = "## 1. Refunds\n- [ ] 1.1 Refund creation a\n- [ ] 1.2 Refund creation b (after: 1.1)\n- [ ] 1.3 Refund creation c (after: 1.2)\n"
    output = lint(make_change(tmp_path, tasks=tasks)).stdout
    assert "WARN" in output and "single chain" in output


def test_done_tasks_are_left_out_of_the_plan(tmp_path):
    tasks = "## 1. Refunds\n- [x] 1.1 Refund creation a\n- [ ] 1.2 Refund creation b (after: 1.1)\n- [ ] 1.3 Refund creation c\n"
    output = lint(make_change(tmp_path, tasks=tasks)).stdout
    assert "level 1: 1.2, 1.3" in output
