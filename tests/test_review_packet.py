"""Behaviour tests for review_packet.py — the shared context file every reviewer reads instead of re-exploring the repo."""

import subprocess
import sys
from pathlib import Path

import pytest

PACKET_SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng-standards/scripts/review_packet.py"


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


def test_small_docs_change_suggests_quick_depth_and_no_specialists(repo):
    write(repo, "docs/guide.md", "Some new docs\n")
    commit_all(repo)

    packet = build_packet(repo)

    assert "Suggested depth: quick" in packet
    assert "performance: no" in packet
    assert "security: no" in packet


def test_data_access_change_flags_performance_review(repo):
    write(repo, "src/InvoiceRepository.kt", "fun findAll() = db.query(\"SELECT * FROM invoice\")\n")
    commit_all(repo)

    assert "performance: yes" in build_packet(repo)


def test_auth_or_dependency_change_flags_security_review(repo):
    write(repo, "src/auth/LoginController.kt", "fun login(password: String) = check(password)\n")
    write(repo, "build.gradle.kts", "dependencies { implementation(\"x:y:1.0\") }\n")
    commit_all(repo)

    packet = build_packet(repo)

    assert "security: yes" in packet


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
