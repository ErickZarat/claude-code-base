# claude-code-base

Personal Claude Code plugin marketplace that distributes engineering standards to every project:
no vibe coding, TDD, reuse-first, interface-first design, secret guard, and iterative PR review cycles.

## Layout
- `.claude-plugin/marketplace.json` — marketplace catalog (name `claude-code-base`).
- `plugins/eng/` — the plugin:
  - `skills/*/SKILL.md` — skills (invoked as `/eng:<name>`).
  - `agents/*.md` — reviewer subagents (`requirements-verifier`, `security-reviewer`, `performance-reviewer`, `code-reviewer`,
    `fix-verifier`); standard/thorough reviews run ALL dedicated reviewers (`tests/test_review_coverage.py`);
    default models must be sonnet/haiku (validator enforces) — opus only per call for thorough reviews.
  - `scripts/review_packet.py` — builds the shared review packet (diff, files, requirement sources, triage).
  - `scripts/github_sync.py` — OpenSpec change → GitHub milestone/epic + task issues; `GitHubClient` port, `GhCliClient` adapter.
    Tests use a fake client — never call the real GitHub API from tests.
  - `hooks/hooks.json` + `hooks/guard_secrets.py` — PreToolUse secret/destructive-command guard.
  - `template/` — files plugins cannot distribute (rules, CLAUDE.md, settings.json, pre-commit, PR template,
    `.github` CI checks + `eng_pr_checklist.py`), copied into projects by `install.sh`.
  - `install.sh` — manifest-based installer/updater (bash 3.2 compatible — macOS default shell).
- `install.sh` (root) — wrapper for clone-based installs.
- `tests/` — pytest behaviour tests for the hook, installer, scripts and the PR-title workflow. `scripts/validate.py` — static checks.

## Commands
| Purpose | Command |
|---|---|
| All checks | `python3 scripts/validate.py && shellcheck install.sh plugins/eng/install.sh && pytest -q` |
| Single test | `pytest -q tests/test_install.py -k conflict` |
| Try plugin changes locally | `claude --plugin-dir ./plugins/eng` |
| Validate plugin (Claude CLI) | `claude plugin validate .` |
| Try installer on a scratch dir | `./install.sh --dry-run /tmp/scratch` |

## Rules for changing this repo
- This repo follows its own standards: TDD for every script, hook and installer change (failing test first).
- Scripts in `plugins/eng/scripts` and `hooks` must run on Python 3.9 (macOS default): `from __future__ import annotations`.
- Never put realistic-looking secrets in tests; build fake values from fragments (see `tests/test_guard_secrets.py`).
- Keep rules short and precise — one line per behaviour. They load into every session of every project.
- Token budget: skill descriptions < 200 chars (sent every request); review skills stay manual-only; reviewers read the packet, output tables.
- Skills/agents: `name` must equal the folder/file name; the `description` decides when Claude uses it — make it specific.
- Every user-visible change: bump `version` in `plugins/eng/.claude-plugin/plugin.json` (semver) and add a
  `CHANGELOG.md` entry. Template changes reach projects only when they re-run `/eng:setup`.
- Breaking a template path (renaming/removing a rule) is a MAJOR bump; note migration steps in the changelog.
- Commits: Conventional Commits. Never force-push `main`.
