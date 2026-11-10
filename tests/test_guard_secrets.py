"""Behaviour tests for the PreToolUse secret guard hook.

Fake secrets are assembled at runtime from fragments so this file itself never contains
something that looks like a real credential (keeps the guard, gitleaks and GitHub push protection quiet).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng-standards/hooks/guard_secrets.py"
BLOCKED_EXIT_CODE = 2
ALLOWED_EXIT_CODE = 0

FAKE_AWS_KEY = "AKIA" + "IOSFODNN7ABCDEFG"
FAKE_GITHUB_TOKEN = "ghp" + "_" + "a" * 36
FAKE_PRIVATE_KEY_HEADER = "-----BEGIN RSA " + "PRIVATE KEY-----"
FAKE_JWT = "eyJ" + "hbGciOiJIUzI1NiJ9" + ".eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0" + "." + "SflKxwRJSMeKKF2QT4fwpM"


def run_hook(tool_name: str, tool_input: dict) -> subprocess.CompletedProcess:
    hook_event = {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(hook_event),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "file_path",
    ["/project/.env", "/project/.env.production", "/project/certs/server.pem", "/home/me/.ssh/id_ed25519", "/home/me/.aws/credentials"],
)
def test_blocks_reading_secret_files(file_path):
    result = run_hook("Read", {"file_path": file_path})
    assert result.returncode == BLOCKED_EXIT_CODE
    assert "secret file" in result.stderr


@pytest.mark.parametrize("file_path", ["/project/.env.example", "/project/.env.sample", "/project/src/Main.kt"])
def test_allows_reading_templates_and_source(file_path):
    assert run_hook("Read", {"file_path": file_path}).returncode == ALLOWED_EXIT_CODE


@pytest.mark.parametrize(
    "content, expected_kind",
    [
        (f'val awsKey = "{FAKE_AWS_KEY}"', "AWS access key id"),
        (f"token: {FAKE_GITHUB_TOKEN}", "GitHub token"),
        (FAKE_PRIVATE_KEY_HEADER, "private key block"),
        (f"Authorization: Bearer {FAKE_JWT}", "JSON Web Token"),
        ('password = "' + "S3cr3t" + 'Pass!"', "hard-coded credential"),
        ("url: postgres://admin:" + "hunter22" + "@db:5432/app", "credentials in connection string"),
    ],
)
def test_blocks_writing_secrets(content, expected_kind):
    result = run_hook("Write", {"file_path": "/project/src/Config.kt", "content": content})
    assert result.returncode == BLOCKED_EXIT_CODE
    assert expected_kind in result.stderr


def test_blocks_secrets_in_edit_and_multiedit():
    edit = run_hook("Edit", {"file_path": "a.kt", "old_string": "x", "new_string": FAKE_GITHUB_TOKEN})
    multi_edit = run_hook("MultiEdit", {"file_path": "a.kt", "edits": [{"old_string": "x", "new_string": FAKE_GITHUB_TOKEN}]})
    assert edit.returncode == BLOCKED_EXIT_CODE
    assert multi_edit.returncode == BLOCKED_EXIT_CODE


@pytest.mark.parametrize(
    "content",
    [
        'password: "${DB_PASSWORD}"',
        "url: postgres://${DB_USER}:${DB_PASSWORD}@db/app",
        'api_key: "<your-api-key>"',
        'val testPassword = "fake-test-pass" // pragma: allowlist secret',
        "val passwordField = request.password",
        "fun total(items: List<Item>) = items.sumOf { it.price }",
    ],
)
def test_allows_placeholders_and_normal_code(content):
    assert run_hook("Write", {"file_path": "/project/app.yml", "content": content}).returncode == ALLOWED_EXIT_CODE


@pytest.mark.parametrize(
    "command, expected_reason",
    [
        ("cat .env | grep DB", "secret file"),
        ("printenv", "dumps all environment variables"),
        ("git add . && git push -f origin main", "force push"),
        ("git push --force-with-lease", "force push"),
        ("git reset --hard HEAD~1", "hard reset"),
        ("git clean -fdx", "git clean"),
    ],
)
def test_blocks_dangerous_commands(command, expected_reason):
    result = run_hook("Bash", {"command": command})
    assert result.returncode == BLOCKED_EXIT_CODE
    assert expected_reason in result.stderr


@pytest.mark.parametrize(
    "command",
    ["git push origin feature/x", "./gradlew test --no-daemon", "FOO=bar ./gradlew build", "cp .env.example .env.example.bak"],
)
def test_allows_normal_commands(command):
    assert run_hook("Bash", {"command": command}).returncode == ALLOWED_EXIT_CODE


def test_ignores_malformed_input():
    result = subprocess.run([sys.executable, str(HOOK_SCRIPT)], input="not json", capture_output=True, text=True, check=False)
    assert result.returncode == ALLOWED_EXIT_CODE
