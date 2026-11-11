#!/usr/bin/env python3
"""
PreToolUse guard for Claude Code.

Blocks, before the tool runs:
  1. Reading or editing secret files (.env, private keys, cloud credentials).
  2. Writing content that looks like a real secret (API keys, tokens, private keys,
     hard-coded passwords, credentialed connection strings).
  3. Shell commands that dump secrets or destroy git history.

How it talks to Claude Code:
  - Receives the tool call as JSON on stdin.
  - Exit 0  -> allow the tool call.
  - Exit 2  -> block it; the message on stderr is shown to Claude so it can correct itself.

False positive on a line you KNOW is safe (e.g. a test fixture)? Add one of these markers
to that line:  "pragma: allowlist secret"  or  "gitleaks:allow".
"""

from __future__ import annotations  # keeps type hints working on macOS's bundled Python 3.9

import json
import os
import re
import sys

BLOCK_EXIT_CODE = 2
ALLOW_MARKERS = ("pragma: allowlist secret", "gitleaks:allow")

# --- 1. Files that must never be read or edited by the agent ---------------------------

# Template env files are safe: they hold placeholders and document required variables.
SAFE_ENV_TEMPLATE_NAMES = {".env.example", ".env.sample", ".env.template", ".env.dist"}

SECRET_FILE_NAME_PATTERNS = [
    re.compile(r"^\.env$"),
    re.compile(r"^\.env\..+$"),                 # .env.local, .env.production, ...
    re.compile(r"^.+\.(pem|key|p12|pfx|jks|keystore)$"),
    re.compile(r"^id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$"),
    re.compile(r"^\.netrc$"),
    re.compile(r"^\.pgpass$"),
    re.compile(r"^credentials(\.json)?$"),       # AWS / GCP credential files
    re.compile(r"^service[-_]?account.*\.json$"),
]
SECRET_DIRECTORY_NAMES = {".aws", ".ssh", ".gnupg", "secrets"}


def is_secret_file(path: str) -> bool:
    """True when the path points at a file that typically holds real credentials."""
    if not path:
        return False
    normalized_path = os.path.normpath(path)
    file_name = os.path.basename(normalized_path)
    if any(file_name.startswith(template_name) for template_name in SAFE_ENV_TEMPLATE_NAMES):
        return False  # .env.example, .env.example.bak, ... hold placeholders only
    if any(pattern.match(file_name) for pattern in SECRET_FILE_NAME_PATTERNS):
        return True
    path_parts = set(normalized_path.split(os.sep))
    return bool(path_parts & SECRET_DIRECTORY_NAMES)


# --- 2. Content that looks like a real secret ------------------------------------------

# High-confidence formats: real provider token shapes. Blocked everywhere, test files included.
HIGH_CONFIDENCE_PATTERNS = {
    "private key block": re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"),
    "AWS access key id": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "Stripe live key": re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{16,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "Anthropic API key": re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b"),
    "OpenAI API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{32,}\b"),
    "JSON Web Token": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
}

# Heuristics: catch hard-coded credentials in production code. Skipped in test files, where fake credentials
# are legitimately needed (e.g. to prove a password does not leak from a connection string).
HEURISTIC_PATTERNS = {
    "hard-coded credential": re.compile(
        r"""(?ix)
        \b(?:password|passwd|pwd|secret|client_secret|api[_-]?key|access[_-]?key|auth[_-]?token|private[_-]?key)\b
        \s*[:=]\s*
        ["']([^"'\s]{8,})["']
        """
    ),
    "credentials in connection string": re.compile(r"\b[a-z][a-z0-9+.\-]*://[^/\s:@'\"]+:([^/\s@'\"]{3,})@"),
}

# Values that are clearly placeholders or references, not real secrets.
PLACEHOLDER_VALUE = re.compile(
    r"""(?ix)
    ^\$\{.*\}$ | ^\$[A-Z_]+$ | ^<.*>$ | ^%.*%$ | ^\{\{.*\}\}$ |
    changeme | change_me | placeholder | example | your[_-] | dummy | redacted | xxxx | \*\*\*\* |
    (?:^|[-_.\s])(?:fake|mock|test|testing|sample)(?:$|[-_.\s\d])
    """
)

TEST_FILE_PATTERN = re.compile(
    r"""(?x)
    (?:^|/)(?:src/(?:test|testFixtures|integrationTest|it)|tests?|__tests__|spec|fixtures|testdata)/ |
    (?:Test|Tests|IT|Spec)\.(?:kt|kts|java|scala|groovy)$ |
    [._-](?:test|spec)\.(?:ts|tsx|js|jsx|mjs|cjs|py|rb)$ |
    (?:^|/)test_[^/]*\.py$ | _test\.(?:go|py)$ | (?:^|/)conftest\.py$
    """
)
MAX_PREVIEW_LENGTH = 80


def is_test_file(path: str) -> bool:
    return bool(path) and bool(TEST_FILE_PATTERN.search(path.replace(os.sep, "/")))


def redacted_preview(line: str, secret_value: str) -> str:
    """The offending line with the secret masked, so Claude can locate it without the value being echoed."""
    preview = line.replace(secret_value, "****").strip()
    return preview if len(preview) <= MAX_PREVIEW_LENGTH else preview[:MAX_PREVIEW_LENGTH] + "…"


def find_secrets(text: str, include_heuristics: bool = True) -> list[str]:
    """Return human-readable findings for every line that looks like it contains a real secret."""
    patterns = {**HIGH_CONFIDENCE_PATTERNS, **(HEURISTIC_PATTERNS if include_heuristics else {})}
    findings = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if any(marker in line for marker in ALLOW_MARKERS):
            continue
        for secret_kind, pattern in patterns.items():
            match = pattern.search(line)
            if not match:
                continue
            captured_value = match.group(1) if match.groups() else match.group(0)
            if PLACEHOLDER_VALUE.search(captured_value):
                continue
            findings.append(f"line {line_number}: {secret_kind} → `{redacted_preview(line, captured_value)}`")
            break
    return findings


def text_being_written(tool_name: str, tool_input: dict) -> str:
    """Collect the new text a Write / Edit / MultiEdit call would put on disk."""
    if tool_name == "Write":
        return tool_input.get("content", "") or ""
    if tool_name == "Edit":
        return tool_input.get("new_string", "") or ""
    if tool_name == "MultiEdit":
        return "\n".join(edit.get("new_string", "") or "" for edit in tool_input.get("edits", []))
    return ""


# --- 3. Dangerous shell commands --------------------------------------------------------

DANGEROUS_COMMAND_PATTERNS = {
    "dumps all environment variables": re.compile(r"(?:^|[;&|]\s*)(?:printenv|env)\s*(?:$|[;&|>])"),
    "force push rewrites shared history": re.compile(r"\bgit\s+push\b[^;&|]*\s(?:-f|--force(?:-with-lease)?)\b"),
    "hard reset discards work": re.compile(r"\bgit\s+reset\s+[^;&|]*--hard\b"),
    "git clean deletes untracked files": re.compile(r"\bgit\s+clean\s+[^;&|]*-[a-zA-Z]*f"),
    "recursive delete of root/home": re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+(?:/|~|\$HOME)(?:\s|$)"),
}


def find_dangerous_command(command: str) -> str | None:
    """Return a reason if the shell command is dangerous or touches secret files."""
    for reason, pattern in DANGEROUS_COMMAND_PATTERNS.items():
        if pattern.search(command):
            return reason
    for token in re.split(r"[\s;&|<>()'\"=]+", command):
        if is_secret_file(token):
            return f"references secret file '{token}'"
    return None


# --- Entry point ------------------------------------------------------------------------

def block(message: str) -> None:
    print(f"[guard_secrets] BLOCKED: {message}", file=sys.stderr)
    sys.exit(BLOCK_EXIT_CODE)


def main() -> None:
    try:
        hook_event = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Malformed input is not ours to judge; let Claude Code handle it.

    tool_name = hook_event.get("tool_name", "")
    tool_input = hook_event.get("tool_input", {}) or {}

    if tool_name in {"Read", "Write", "Edit", "MultiEdit"}:
        target_path = tool_input.get("file_path", "")
        if is_secret_file(target_path):
            block(
                f"'{target_path}' is a secret file. Do not read or modify it. "
                "Document required variables in .env.example with placeholder values and ask the user to set real values."
            )

    if tool_name in {"Write", "Edit", "MultiEdit"}:
        target_path = tool_input.get("file_path", "")
        findings = find_secrets(text_being_written(tool_name, tool_input), include_heuristics=not is_test_file(target_path))
        if findings:
            block(
                "content looks like a hard-coded secret (" + "; ".join(findings) + "). "
                "Load it from configuration / environment / a secret manager instead. "
                "If it is a deliberate fake value, mark THAT line with 'pragma: allowlist secret'. "
                "Do not retry with reworded content to get past this guard — fix the flagged line or ask the user."
            )

    if tool_name == "Bash":
        reason = find_dangerous_command(tool_input.get("command", "") or "")
        if reason:
            block(f"shell command {reason}. Ask the user to run it themselves if it is really needed.")

    sys.exit(0)


if __name__ == "__main__":
    main()
