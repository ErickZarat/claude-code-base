"""Behaviour tests for the project installer (install / update / conflict / ignore / user mode)."""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "plugins/eng-standards"
SAMPLE_RULE = ".claude/rules/security.md"


@pytest.fixture
def plugin_copy(tmp_path):
    """A disposable copy of the plugin, so tests can simulate a new release by editing its template."""
    copy_dir = tmp_path / "plugin"
    shutil.copytree(PLUGIN_DIR, copy_dir)
    return copy_dir


@pytest.fixture
def project(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".gitignore").write_text("node_modules\n")
    return project_dir


def run_installer(plugin_dir: Path, *args: str, home: Path | None = None) -> str:
    env = None if home is None else {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    result = subprocess.run(
        ["bash", str(plugin_dir / "install.sh"), *args], capture_output=True, text=True, check=True, env=env
    )
    return result.stdout


def release_new_rule_version(plugin_dir: Path, extra_line: str = "- New rule line.\n") -> None:
    rule_file = plugin_dir / "template" / SAMPLE_RULE
    rule_file.write_text(rule_file.read_text() + extra_line)


def test_fresh_install_creates_rules_seeds_manifest_and_gitignore(plugin_copy, project):
    run_installer(plugin_copy, str(project))

    assert (project / SAMPLE_RULE).is_file()
    assert (project / "CLAUDE.md").is_file()
    assert (project / ".claude/settings.json").is_file()
    assert (project / ".pre-commit-config.yaml").is_file()
    assert SAMPLE_RULE in (project / ".claude/.eng-standards-manifest").read_text()
    assert (project / ".claude/.eng-standards-version").read_text().strip() == "1.0.0"
    gitignore = (project / ".gitignore").read_text().splitlines()
    assert "node_modules" in gitignore and ".env" in gitignore and "*.eng-new" in gitignore


def test_reinstall_is_idempotent(plugin_copy, project):
    run_installer(plugin_copy, str(project))
    gitignore_before = (project / ".gitignore").read_text()

    output = run_installer(plugin_copy, str(project))

    assert "Created:" not in output and "Updated:" not in output
    assert (project / ".gitignore").read_text() == gitignore_before


def test_update_replaces_untouched_rules(plugin_copy, project):
    run_installer(plugin_copy, str(project))
    release_new_rule_version(plugin_copy)

    output = run_installer(plugin_copy, str(project))

    assert "Updated:" in output
    assert "New rule line." in (project / SAMPLE_RULE).read_text()


def test_update_keeps_locally_modified_rules_and_writes_eng_new(plugin_copy, project):
    run_installer(plugin_copy, str(project))
    (project / SAMPLE_RULE).write_text("my team's own security rules\n")
    release_new_rule_version(plugin_copy)

    output = run_installer(plugin_copy, str(project))

    assert "Locally modified" in output
    assert (project / SAMPLE_RULE).read_text() == "my team's own security rules\n"
    assert "New rule line." in (project / (SAMPLE_RULE + ".eng-new")).read_text()

    # Still recognised as modified on the next run (not silently overwritten later).
    release_new_rule_version(plugin_copy, "- Another rule.\n")
    run_installer(plugin_copy, str(project))
    assert (project / SAMPLE_RULE).read_text() == "my team's own security rules\n"


def test_seed_files_are_never_overwritten(plugin_copy, project):
    run_installer(plugin_copy, str(project))
    (project / "CLAUDE.md").write_text("# My project\n")

    run_installer(plugin_copy, str(project))

    assert (project / "CLAUDE.md").read_text() == "# My project\n"


def test_ignored_paths_are_not_reinstalled(plugin_copy, project):
    run_installer(plugin_copy, str(project))
    python_rule = project / ".claude/rules/lang/python.md"
    python_rule.unlink()
    (project / ".claude/.eng-standards-ignore").write_text("# not a python project\n.claude/rules/lang/python.md\n")

    output = run_installer(plugin_copy, str(project))

    assert not python_rule.exists()
    assert "Skipped" in output


def test_dry_run_writes_nothing(plugin_copy, project):
    output = run_installer(plugin_copy, "--dry-run", str(project))

    assert "dry run" in output
    assert not (project / ".claude").exists()
    assert (project / ".gitignore").read_text() == "node_modules\n"


def test_user_mode_installs_only_rules_into_home(plugin_copy, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    run_installer(plugin_copy, "--user", home=fake_home)

    assert (fake_home / SAMPLE_RULE).is_file()
    assert not (fake_home / "CLAUDE.md").exists()
    assert not (fake_home / ".claude/settings.json").exists()
