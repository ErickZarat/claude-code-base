#!/usr/bin/env python3
"""
API contract breaking-change check (installed by eng@claude-code-base).

For files changed in the PR:
  - .proto      → `buf breaking` against the base branch (needs buf.yaml / buf.work.yaml / buf.gen.yaml in the repo)
  - OpenAPI     → `oasdiff breaking` base vs PR version (files named *openapi*/*swagger*, or YAML/JSON starting with
                  `openapi:` / `swagger:`)
  - .graphql / .avsc → listed for manual review (no automatic check)
Tools run from their Docker images (bufbuild/buf, tufin/oasdiff), so nothing has to be installed.

A breaking change fails the check unless the PR body contains a line
  Breaking-change: approved — <reason / migration plan>

Environment: BASE_REF (target branch, default main), PR_BODY.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

OPENAPI_NAME = re.compile(r"(?i)(openapi|swagger)[^/]*\.(ya?ml|json)$")
OPENAPI_CONTENT = re.compile(r'^\s*["\']?(openapi|swagger)["\']?\s*:', re.MULTILINE)
APPROVAL = re.compile(r"(?im)^\s*Breaking-change:\s*approved\b")
BUF_CONFIGS = ("buf.yaml", "buf.work.yaml")


@dataclass
class Check:
    name: str
    command: list[str]
    base_file: str | None = None  # OpenAPI: path whose base-branch version must be extracted first


def classify_contract_files(paths: list[str], read: Callable[[str], str]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in paths:
        kind = None
        if path.endswith(".proto"):
            kind = "proto"
        elif path.endswith((".graphql", ".graphqls", ".gql")):
            kind = "graphql"
        elif path.endswith(".avsc"):
            kind = "avro"
        elif OPENAPI_NAME.search(path) or (path.endswith((".yaml", ".yml", ".json"))
                                           and OPENAPI_CONTENT.search(read(path)[:2000])):
            kind = "openapi"
        if kind:
            found.setdefault(kind, []).append(path)
    return found


def plan_checks(contracts: dict[str, list[str]], base_ref: str, has_buf_config: bool,
                existed_at_base: Callable[[str], bool]) -> tuple[list[Check], list[str]]:
    checks: list[Check] = []
    notes: list[str] = []
    if contracts.get("proto"):
        if has_buf_config:
            checks.append(Check("buf breaking", ["docker", "run", "--rm", "-v", f"{os.getcwd()}:/workspace",
                                                 "-w", "/workspace", "bufbuild/buf", "breaking",
                                                 "--against", f".git#ref=origin/{base_ref}"]))
        else:
            notes.append("Proto files changed but no buf.yaml found — add one to enable automatic breaking-change "
                         f"checks. Review manually: {', '.join(contracts['proto'])}")
    for path in contracts.get("openapi", []):
        if existed_at_base(path):
            checks.append(Check(f"oasdiff {path}", ["docker", "run", "--rm", "-v", "{base_dir}:/base:ro",
                                                     "-v", f"{os.getcwd()}:/rev:ro", "tufin/oasdiff", "breaking",
                                                     "/base/spec", f"/rev/{path}", "--fail-on", "ERR"],
                                base_file=path))
        else:
            notes.append(f"{path} is new in this PR — nothing to compare against.")
    for kind in ("graphql", "avro"):
        for path in contracts.get(kind, []):
            notes.append(f"{path} ({kind}) changed — no automatic check; reviewers must confirm compatibility.")
    return checks, notes


def exit_code(breaking_found: bool, pr_body: str) -> int:
    return 0 if not breaking_found or APPROVAL.search(pr_body or "") else 1


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def run_check(check: Check, base_ref: str) -> bool:
    """Returns True when the check found a breaking change."""
    command = check.command
    if check.base_file:
        base_dir = tempfile.mkdtemp()
        Path(base_dir, "spec").write_text(git("show", f"origin/{base_ref}:{check.base_file}").stdout)
        command = [part.replace("{base_dir}", base_dir) for part in command]
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command).returncode != 0


def main() -> int:
    base_ref = os.environ.get("BASE_REF") or "main"
    pr_body = os.environ.get("PR_BODY", "")
    changed = [line for line in git("diff", "--name-only", f"origin/{base_ref}...HEAD").stdout.splitlines() if line]
    existing = [path for path in changed if Path(path).is_file()]
    contracts = classify_contract_files(existing, lambda path: Path(path).read_text(errors="ignore"))
    if not contracts:
        print("No API contract changes.")
        return 0

    checks, notes = plan_checks(contracts, base_ref, any(Path(name).is_file() for name in BUF_CONFIGS),
                                lambda path: git("cat-file", "-e", f"origin/{base_ref}:{path}").returncode == 0)
    for note in notes:
        print(f"::warning::{note}")
    breaking = [check.name for check in checks if run_check(check, base_ref)]
    if breaking:
        print(f"Breaking changes found by: {', '.join(breaking)}")
    code = exit_code(bool(breaking), pr_body)
    if breaking and code == 0:
        print("::warning::Breaking change approved in the PR body (Breaking-change: approved).")
    elif breaking:
        print("::error::Breaking API change. Version the API / keep backwards compatibility, or add "
              "'Breaking-change: approved — <reason and migration plan>' to the PR body.")
    return code


if __name__ == "__main__":
    sys.exit(main())
