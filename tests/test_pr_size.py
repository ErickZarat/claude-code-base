"""Behaviour tests for pr_size.py — a PR must stay small enough to review well."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/scripts/pr_size.py"


def git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "dev@example.test")
    git(repo, "config", "user.name", "Dev")
    (repo / "README.md").write_text("hello\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")
    git(repo, "checkout", "-qb", "feature")
    return repo


def add_file(repo, relative, lines):
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"line {n}\n" for n in range(lines)))


def commit(repo):
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "work")


def run(repo, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--base", "main", *args], cwd=repo, capture_output=True, text=True)


def test_small_pr_passes(tmp_path):
    repo = make_repo(tmp_path)
    add_file(repo, "src/refunds/service.ts", 120)
    commit(repo)
    result = run(repo)
    assert result.returncode == 0
    assert "120 changed lines" in result.stdout


def test_pr_over_the_budget_fails_and_shows_where_the_lines_are(tmp_path):
    repo = make_repo(tmp_path)
    add_file(repo, "renderer/app.ts", 400)
    add_file(repo, "components/src/price.tsx", 300)
    commit(repo)
    result = run(repo, "--max", "600")
    assert result.returncode == 1
    assert "700 changed lines > 600" in result.stdout
    assert "renderer/" in result.stdout and "components/" in result.stdout


def test_lockfiles_snapshots_and_golden_files_do_not_count(tmp_path):
    repo = make_repo(tmp_path)
    add_file(repo, "src/app.ts", 50)
    for generated in ("pnpm-lock.yaml", "package-lock.json", "yarn.lock", "gradle.lockfile",
                      "src/__snapshots__/app.test.ts.snap", "test/golden/home.html", "dist/app.js"):
        add_file(repo, generated, 500)
    commit(repo)
    result = run(repo)
    assert result.returncode == 0, result.stdout
    assert "50 changed lines" in result.stdout


def test_budget_comes_from_the_environment(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    add_file(repo, "src/app.ts", 300)
    commit(repo)
    monkeypatch.setenv("ENG_PR_MAX_LINES", "200")
    assert run(repo).returncode == 1
