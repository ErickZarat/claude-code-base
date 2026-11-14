"""Behaviour tests for review_packet.py — the shared context file every reviewer reads instead of re-exploring the repo."""

import subprocess
import sys
from pathlib import Path

import pytest

PACKET_SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/review_packet.py"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def write(repo: Path, relative_path: str, content: str) -> None:
    file_path = repo / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)


@pytest.fixture
def repo(tmp_path):
    """A git repo with a `main` base commit and a `feature` branch checked out."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    git(repo_dir, "init", "-q", "-b", "main")
    git(repo_dir, "config", "user.email", "test@example.com")
    git(repo_dir, "config", "user.name", "Test")
    write(repo_dir, "README.md", "# demo\n")
    git(repo_dir, "add", "-A")
    git(repo_dir, "commit", "-q", "-m", "base")
    git(repo_dir, "checkout", "-q", "-b", "feature")
    return repo_dir


def commit_all(repo: Path) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change")


def build_packet(repo: Path, *extra_args: str) -> str:
    output_file = repo / ".reviews/packet.md"
    subprocess.run(
        [sys.executable, str(PACKET_SCRIPT), "--base", "main", "--out", str(output_file), *extra_args],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    return output_file.read_text()


def test_packet_contains_changed_files_and_diff(repo):
    write(repo, "src/Invoice.kt", "data class Invoice(val id: String)\n")
    commit_all(repo)

    packet = build_packet(repo)

    assert "src/Invoice.kt" in packet
    assert "+data class Invoice(val id: String)" in packet


def test_small_change_still_gets_the_full_standard_review(repo):
    write(repo, "docs/guide.md", "Some new docs\n")
    commit_all(repo)

    packet = build_packet(repo)

    assert "Suggested depth: standard" in packet
    assert "quick" not in packet.split("## Triage")[1].split("## Requirement sources")[0]
    assert "performance focus: no" in packet
    assert "security focus: no" in packet


def test_data_access_change_flags_performance_review(repo):
    write(repo, "src/InvoiceRepository.kt", "fun findAll() = db.query(\"SELECT * FROM invoice\")\n")
    commit_all(repo)

    assert "performance focus: yes" in build_packet(repo)


def test_auth_or_dependency_change_flags_security_review(repo):
    write(repo, "src/auth/LoginController.kt", "fun login(password: String) = check(password)\n")
    write(repo, "build.gradle.kts", "dependencies { implementation(\"x:y:1.0\") }\n")
    commit_all(repo)

    packet = build_packet(repo)

    assert "security focus: yes" in packet


def test_large_change_suggests_standard_depth(repo):
    write(repo, "src/Big.kt", "".join(f"val value{i} = {i}\n" for i in range(120)))
    commit_all(repo)

    assert "Suggested depth: standard" in build_packet(repo)


def test_lists_openspec_requirement_sources(repo):
    write(repo, "openspec/changes/add-refunds/proposal.md", "# Add refunds\n")
    write(repo, "openspec/changes/add-refunds/tasks.md", "- [ ] 1.1 refund endpoint\n")
    write(repo, "openspec/changes/add-refunds/specs/billing/spec.md", "### Requirement: Refund\n")
    write(repo, "openspec/changes/archive/old/proposal.md", "# old\n")
    write(repo, "src/Refund.kt", "class Refund\n")
    commit_all(repo)

    requirement_section = build_packet(repo).split("## Requirement sources")[1].split("## Changed files")[0]

    assert "openspec/changes/add-refunds/tasks.md" in requirement_section
    assert "openspec/changes/add-refunds/specs/billing/spec.md" in requirement_section
    assert "archive/old" not in requirement_section


def test_since_option_limits_diff_to_remediation_commits(repo):
    write(repo, "src/A.kt", "class A\n")
    commit_all(repo)
    first_round_head = git(repo, "rev-parse", "HEAD").strip()
    write(repo, "src/B.kt", "class B\n")
    commit_all(repo)

    packet = build_packet(repo, "--since", first_round_head)

    assert "src/B.kt" in packet
    assert "src/A.kt" not in packet


def test_huge_diffs_are_truncated_with_a_notice(repo):
    write(repo, "src/Huge.kt", "".join(f"val line{i} = \"{'x' * 50}\"\n" for i in range(4000)))
    commit_all(repo)

    packet = build_packet(repo, "--max-diff-lines", "200")

    assert "diff truncated" in packet
    assert len(packet.splitlines()) < 400


def test_project_minimum_depth_raises_the_suggestion(repo):
    write(repo, "CLAUDE.md", "# Project\n\n## Review\nMinimum review depth: thorough\n")
    write(repo, "docs/guide.md", "tiny docs change\n")
    commit_all(repo)

    packet = build_packet(repo)

    assert "Suggested depth: thorough" in packet
    assert "project minimum" in packet


def test_a_quick_minimum_never_lowers_the_default(repo):
    write(repo, "CLAUDE.md", "Minimum review depth: quick\n")
    write(repo, "src/Small.kt", "class Small\n")
    commit_all(repo)

    assert "Suggested depth: standard" in build_packet(repo)


def test_thorough_minimum_is_respected(repo):
    write(repo, "CLAUDE.md", "Minimum review depth: thorough\n")
    write(repo, "src/A.kt", "class A\n")
    commit_all(repo)

    assert "Suggested depth: thorough" in build_packet(repo)


# --- v2.6.0: dynamic SQL candidates (possible SQL injection) ---------------------------------

def dynamic_sql_section(packet: str) -> str:
    return packet.split("## Dynamic SQL candidates")[1].split("\n## ")[0]


def test_lists_sql_built_with_string_templates_or_concatenation(repo):
    write(repo, "src/RefundRepository.kt", "\n".join([
        "class RefundRepository(private val jdbc: Jdbc) {",
        '    fun byId(id: String) = jdbc.query("SELECT * FROM refund WHERE id = $id")',
        '    fun sorted(column: String) = jdbc.query("SELECT * FROM refund ORDER BY ${column}")',
        '    fun byOrder(orderId: String) = jdbc.query("SELECT * FROM refund WHERE order_id = \'" + orderId + "\'")',
        '    fun safe(id: String) = jdbc.query("SELECT * FROM refund WHERE id = ?", id)',
        '    fun named(id: String) = jdbc.query("SELECT * FROM refund WHERE id = :id", mapOf("id" to id))',
        "}",
    ]) + "\n")
    write(repo, "app/queries.py", 'cursor.execute(f"DELETE FROM refund WHERE id = {refund_id}")\n'
                                   'cursor.execute("UPDATE refund SET state = %s WHERE id = %s" % (state, rid))\n'
                                   'cursor.execute("SELECT * FROM refund WHERE id = %s", (rid,))\n')
    commit_all(repo)

    section = dynamic_sql_section(build_packet(repo))

    assert "src/RefundRepository.kt:2" in section
    assert "src/RefundRepository.kt:3" in section
    assert "src/RefundRepository.kt:4" in section
    assert "src/RefundRepository.kt:5" not in section and "src/RefundRepository.kt:6" not in section
    assert "app/queries.py:1" in section and "app/queries.py:2" in section
    assert "app/queries.py:3" not in section


def test_no_dynamic_sql_says_none(repo):
    write(repo, "src/A.kt", 'val greeting = "Hello $name"\n')
    commit_all(repo)

    assert "none found" in dynamic_sql_section(build_packet(repo))


def test_lists_changed_api_contracts_for_reviewers(repo):
    write(repo, "api/refund.proto", "syntax = \"proto3\";\nmessage Refund { string id = 1; }\n")
    write(repo, "docs/openapi.yaml", "openapi: 3.0.3\n")
    write(repo, "src/A.kt", "class A\n")
    commit_all(repo)

    section = build_packet(repo).split("## Contract changes")[1].split("\n## ")[0]

    assert "api/refund.proto" in section and "docs/openapi.yaml" in section and "src/A.kt" not in section


# --- v3.4: graphify impact — code outside the diff that depends on what changed --------------------

def write_graph(repo: Path, nodes, links) -> None:
    import json
    write(repo, "graphify-out/graph.json", json.dumps({"directed": True, "nodes": nodes, "links": links}))


def impact_section(packet: str) -> str:
    return packet.split("## Impact (graphify)")[1].split("\n## ")[0]


def test_impact_lists_files_outside_the_diff_that_depend_on_changed_code(repo):
    write(repo, "src/refund_service.py", "def refund():\n    return 1\n")
    commit_all(repo)
    write_graph(repo, [
        {"id": "refund", "label": "refund()", "source_file": "src/refund_service.py"},
        {"id": "consumer", "label": "RefundConsumer.handle", "source_file": "src/refund_consumer.py"},
        {"id": "api", "label": "RefundController.post", "source_file": "src/api.py"},
        {"id": "logger", "label": "log()", "source_file": "src/logging.py"},
    ], [
        {"source": "consumer", "target": "refund", "relation": "calls"},
        {"source": "api", "target": "refund", "relation": "calls"},
        {"source": "refund", "target": "logger", "relation": "calls"},  # outgoing: not a dependent
    ])
    section = impact_section(build_packet(repo))
    assert "`src/refund_consumer.py` → RefundConsumer.handle calls refund()" in section
    assert "`src/api.py`" in section
    assert "src/logging.py" not in section


def test_dependents_inside_the_diff_are_not_repeated(repo):
    write(repo, "src/a.py", "x = 1\n")
    write(repo, "src/b.py", "y = 2\n")
    commit_all(repo)
    write_graph(repo, [{"id": "a", "label": "A", "source_file": "src/a.py"},
                       {"id": "b", "label": "B", "source_file": "src/b.py"}],
                [{"source": "b", "target": "a", "relation": "calls"}])
    assert "no dependents outside the diff" in impact_section(build_packet(repo))


def test_without_a_graph_the_impact_section_says_how_to_get_one(repo):
    write(repo, "src/a.py", "x = 1\n")
    commit_all(repo)
    assert "graphify not set up" in impact_section(build_packet(repo))


def test_absolute_source_paths_in_the_graph_are_matched(repo):
    write(repo, "src/a.py", "x = 1\n")
    commit_all(repo)
    write_graph(repo, [{"id": "a", "label": "A", "source_file": str(repo / "src/a.py")},
                       {"id": "c", "label": "C", "source_file": str(repo / "src/c.py")}],
                [{"source": "c", "target": "a", "relation": "imports"}])
    assert "`src/c.py` → C imports A" in impact_section(build_packet(repo))
