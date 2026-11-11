"""Behaviour tests for the PreToolUse secret guard hook.

Fake secrets are assembled at runtime from fragments so this file itself never contains
something that looks like a real credential (keeps the guard, gitleaks and GitHub push protection quiet).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_SCRIPT = Path(__file__).resolve().parents[1] / "plugins/eng/hooks/guard_secrets.py"
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


# --- v1.2.0: test files may contain obviously fake credentials (needed to test credential-leak fixes) ---

FAKE_URL_WITH_CREDENTIALS = "jdbc:postgresql://user:" + "pass" + "@host/db"


@pytest.mark.parametrize(
    "test_file_path",
    [
        "/repo/server-data/src/test/kotlin/com/acme/dao/DatabaseFactoryTest.kt",
        "/repo/src/integrationTest/java/com/acme/RepoIT.java",
        "/repo/tests/test_config.py",
        "/repo/web/src/config.spec.ts",
        "/repo/pkg/db/db_test.go",
        "/repo/src/__tests__/auth.test.js",
    ],
)
def test_allows_heuristic_credentials_in_test_files(test_file_path):
    content = f'val url = "{FAKE_URL_WITH_CREDENTIALS}"\nval password = "' + "S3cr3t" + 'Pass!"\n'
    assert run_hook("Write", {"file_path": test_file_path, "content": content}).returncode == ALLOWED_EXIT_CODE


def test_still_blocks_real_looking_tokens_in_test_files():
    result = run_hook("Write", {"file_path": "/repo/src/test/kotlin/AwsTest.kt", "content": f'val key = "{FAKE_AWS_KEY}"'})
    assert result.returncode == BLOCKED_EXIT_CODE


def test_still_blocks_connection_string_credentials_in_production_code():
    result = run_hook("Write", {"file_path": "/repo/src/main/kotlin/Db.kt", "content": f'val url = "{FAKE_URL_WITH_CREDENTIALS}"'})
    assert result.returncode == BLOCKED_EXIT_CODE


def test_values_marked_fake_are_placeholders_anywhere():
    content = 'val password = "fake-db-password"\nval token = "test-token-value"'
    assert run_hook("Write", {"file_path": "/repo/src/main/kotlin/Dev.kt", "content": content}).returncode == ALLOWED_EXIT_CODE


def test_block_message_shows_which_line_with_value_redacted():
    content = "val a = 1\nval b = 2\n" + f'val url = "{FAKE_URL_WITH_CREDENTIALS}"'
    result = run_hook("Write", {"file_path": "/repo/src/main/kotlin/Db.kt", "content": content})
    assert "line 3" in result.stderr
    assert "val url" in result.stderr
    assert "pass@" not in result.stderr  # the secret itself is never echoed


# --- v2.6.0: shell words are not file reads (reported false positives: "key", "credentials", "secrets") -----

@pytest.mark.parametrize(
    "command",
    [
        'grep -rn "credentials" src/',
        "rg -i secrets docs/",
        "kubectl get secrets -n app",
        "helm upgrade app ./chart --set auth.key=abc",
        'grep -rn "api.key" src',
        "ls src/main/kotlin/com/acme/secrets/",
        'git commit -m "[ISSUE-4] fix: rotate signing key and credentials handling"',
        "./gradlew test --tests '*SecretsServiceTest*'",
    ],
)
def test_ordinary_words_in_shell_commands_are_allowed(command):
    result = run_hook("Bash", {"command": command})
    assert result.returncode == ALLOWED_EXIT_CODE, result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "cat .env",
        "grep password .env",
        "cat ~/.aws/credentials",
        "less config/server.key",
        "cp .env /tmp/copy",
        "source .env.production",
        "cat credentials",
        "base64 k8s/secrets/db.yaml",
        "head -n 5 ./signing.key",
        "cat id_rsa",
    ],
)
def test_reading_real_secret_files_is_still_blocked(command):
    result = run_hook("Bash", {"command": command})
    assert result.returncode == BLOCKED_EXIT_CODE
    assert "secret file" in result.stderr


def test_source_code_inside_a_secrets_package_is_not_a_secret_file():
    path = "/repo/src/main/kotlin/com/acme/secrets/SecretRotationService.kt"
    assert run_hook("Read", {"file_path": path}).returncode == ALLOWED_EXIT_CODE


def test_data_files_inside_a_secrets_folder_are_still_blocked():
    assert run_hook("Read", {"file_path": "/repo/k8s/secrets/db.yaml"}).returncode == BLOCKED_EXIT_CODE
