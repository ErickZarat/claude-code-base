"""Behaviour tests for trace.py — which OpenSpec scenarios have a test that claims them (`spec: <capability>/<scenario>`)."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/trace.py"

SPEC = """## ADDED Requirements

### Requirement: Refund creation
#### Scenario: Valid refund is created
- **WHEN** a paid order is refunded
- **THEN** a refund is created

#### Scenario: Refund above total is rejected
- **WHEN** the amount exceeds the total
- **THEN** the request fails with 422

## REMOVED Requirements
### Requirement: Manual refunds
#### Scenario: Old manual path
- **WHEN** x
- **THEN** y
"""


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run(root: Path, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=root, capture_output=True, text=True)


def project(tmp_path):
    write(tmp_path, "openspec/changes/add-refunds/specs/billing/spec.md", SPEC)
    write(tmp_path, "openspec/specs/catalog/spec.md",
          "### Requirement: Listing\n#### Scenario: Lists products\n- **WHEN** listing\n- **THEN** products\n")
    return tmp_path


def test_reports_untested_scenarios_of_a_change(tmp_path):
    root = project(tmp_path)
    write(root, "src/test/kotlin/RefundTest.kt", '// spec: billing/valid-refund-is-created\nclass RefundTest\n')

    result = run(root, "--change", "openspec/changes/add-refunds")

    assert "billing/refund-above-total-is-rejected" in result.stdout.split("Untested")[1]
    assert "billing/valid-refund-is-created" in result.stdout.split("Untested")[0]
    assert "old-manual-path" not in result.stdout  # removed requirements need no tests
    assert result.returncode == 0  # report only by default


def test_fail_untested_flag_blocks(tmp_path):
    root = project(tmp_path)
    assert run(root, "--change", "openspec/changes/add-refunds", "--fail-untested").returncode == 1


def test_all_covered_passes_with_fail_flag(tmp_path):
    root = project(tmp_path)
    write(root, "tests/test_refunds.py", "# spec: billing/valid-refund-is-created\n"
                                         "def test_x(): pass  # spec: billing/refund-above-total-is-rejected\n")
    result = run(root, "--change", "openspec/changes/add-refunds", "--fail-untested")
    assert result.returncode == 0, result.stdout


def test_main_specs_are_traced_without_change(tmp_path):
    root = project(tmp_path)
    result = run(root)
    assert "catalog/lists-products" in result.stdout


def test_markers_pointing_at_unknown_scenarios_are_reported_as_stale(tmp_path):
    root = project(tmp_path)
    write(root, "web/src/refund.spec.ts", "// spec: billing/refund-was-renamed\n")
    result = run(root, "--change", "openspec/changes/add-refunds")
    assert "Stale" in result.stdout and "billing/refund-was-renamed" in result.stdout


def test_markers_outside_test_files_do_not_count(tmp_path):
    root = project(tmp_path)
    write(root, "src/main/kotlin/Refund.kt", "// spec: billing/valid-refund-is-created\n")
    result = run(root, "--change", "openspec/changes/add-refunds")
    assert "billing/valid-refund-is-created" in result.stdout.split("Untested")[1]


def test_list_prints_ids_to_use_in_tests(tmp_path):
    root = project(tmp_path)
    result = run(root, "--change", "openspec/changes/add-refunds", "--list")
    assert "billing/valid-refund-is-created" in result.stdout
    assert "Refund creation" in result.stdout
