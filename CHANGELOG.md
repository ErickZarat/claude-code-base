# Changelog

All notable changes to the `eng-standards` plugin. Versions follow semver; the version lives in
`plugins/eng-standards/.claude-plugin/plugin.json`.

## [2.2.0] — 2026-11-11
### Changed
- Review finding IDs carry their type/severity: `R<round>-<code>-<n>` with codes `BLK` (blocker), `MAJ` (major),
  `MIN` (minor), `S` (suggestion), `Q` (question) — e.g. `R1-MAJ-29`, `R1-Q-29`, `R1-S-29`. One running number per
  ledger; when severity/type changes the old ID is `SUPERSEDED → <new ID>`. Existing ledgers keep their old IDs.
- Review remediation commits start with the ticket tag: `[ISSUE-44] fix(review): R1-BLK-1 …`.

## [2.1.0] — 2026-11-11
### Changed
- `/eng:epic` defaults to **milestone tracking**: one milestone per OpenSpec change plus a `change:<name>` label on
  every ticket. GitHub's Epic issue type is organization-only, so personal/free repos never showed epics.
  `--tracking epic` (parent issue + sub-issues) and `--tracking both` remain; changes synced with 2.0 keep epic mode.

### Added
- PR checklists: `/eng:task` writes *Acceptance criteria* (from the spec scenarios), *Definition of Done* and
  *Pending decisions* checklists, checks only items proven by tests/DoD results, sets milestone + labels, and keeps
  the PR draft while anything is open.
- Template `.github/pull_request_template.md` (project-owned) with the same sections.
- Template CI `eng-pr-checklist.yml` + `.github/scripts/eng_pr_checklist.py`: a ready PR must link its issue
  (`Closes #n`) and have every checklist item checked; drafts only get a report.
- Review cycle: PR checklist is an exit criterion; a checked criterion without a test is a BLOCKER.

Run `/eng:setup` in each project to install the new template files.

## [2.0.0] — 2026-11-11
### ⚠️ Breaking — plugin renamed `eng-standards` → `eng`, short commands
| Old | New |
|---|---|
| `/eng-standards:setup` | `/eng:setup` |
| `/eng-standards:bootstrap-project` | `/eng:bootstrap` |
| `/eng-standards:definition-of-done` | `/eng:dod` |
| `/eng-standards:review-cycle` | `/eng:review` |
| `/eng-standards:pr-review` | `/eng:review-once` |

**Migration (once per machine, then per project):**
```text
/plugin uninstall eng-standards@claude-code-base
/plugin marketplace update claude-code-base
/plugin install eng@claude-code-base        # user scope
/eng:setup                                  # in each project: renames the plugin id in .claude/settings.json,
                                            # installs the PR-title check and the updated workflow rule
```
Review ledgers moved to a per-branch folder: `openspec/changes/<change>/reviews/<branch>/ledger.md`.

### Added — ticket tracking, one PR per task
- `/eng:epic`: OpenSpec change → GitHub epic + one linked ticket (sub-issue) per task, or per section with
  `--group-by section`. Writes `[ISSUE-n]` into `tasks.md` and a `github.json` mapping; idempotent re-sync;
  labels `epic`/`task`; `ISSUE-` autolink; offers squash-merge-with-PR-title repo setting.
- `/eng:task <n|next>`: one ticket → branch `issue-<n>-<slug>` → TDD → `/eng:dod` → `[ISSUE-n]` commits →
  draft PR `[ISSUE-n] <type>: <task>` (`Closes #n`, `Part of #epic`) → review cycle → ready + verdict comment.
  `next` picks the first ticket that is not done, still open and has no PR. `--stack` for dependent tickets.
- `scripts/github_sync.py` (GitHub behind a port; `gh` CLI adapter) with tests on Python 3.9+.
- Template: `.github/workflows/eng-pr-title.yml` requires PR titles to start with `[ISSUE-n] ` or `[NO-ISSUE] `
  (title passed via env — no script injection; bots exempt).
- Rule (`workflow.md`): one branch + PR per ticket, `[ISSUE-n]` on commits and PR titles, DoD + review cycle on every task PR.

## [1.2.0] — 2026-11-10
### Fixed — review-cycle infinite loop (same finding reopened 3×, fixes blocked by the secret guard)
- Secret guard: heuristic checks (`password = "…"`, `user:pass@host` URLs) are skipped in test files, so tests can
  prove credentials don't leak. Real token formats (AWS, GitHub, Stripe, private keys, JWT…) are still blocked
  everywhere. Values containing fake/mock/test/sample count as placeholders.
- Secret guard messages show the flagged line (secret redacted) and tell Claude not to retry with reworded content.
- review-cycle: findings carry a fingerprint (component · problem class) matched against all ledger rows, so
  variants of a known problem reuse the ID instead of becoming new findings. `Seen` count in the ledger.
  2nd occurrence → fix the root cause across all variants; 3rd → stop and ask. A hook/tool blocking the same fix
  twice → stop and ask.
- Rule (workflow.md): never reword/obfuscate to get past a hook or guard; same error twice → stop and ask.
  Re-run `/eng-standards:setup` in projects to receive it.

## [1.1.0] — 2026-11-10
### Changed — token usage (reviews were ~79% of usage, driven by subagents)
- Reviewer agents default to cheaper models: `requirements-verifier`, `performance-reviewer` → sonnet
  (were opus); `thorough` depth escalates to opus per call.
- `pr-review` now has depth modes chosen by triage: **quick** (1 reviewer), **standard** (2–3), **thorough** (full fan-out).
  pr-review-toolkit agents only run in thorough.
- Reviewers read one shared **review packet** (`scripts/review_packet.py`: diff, changed files, requirement sources,
  triage) instead of exploring the repo independently.
- Deterministic gates (build, tests, lint, gitleaks, semgrep) run before any reviewer; reviewers don't repeat them.
- `review-cycle`: re-review rounds read only the remediation diff; VERIFY rounds use the new `fix-verifier` (haiku);
  default max rounds 5 → 3; ledger carries state instead of pasted reports.
- `pr-review`, `review-cycle` are manual-only (`disable-model-invocation`) and all skill descriptions shortened
  (< 150 chars) — they're sent on every request.
- Reviewer output is tables only, capped per reviewer.
### Added
- `code-reviewer` agent (quality + security + tests + architecture in one pass) and `fix-verifier` agent.
- Installer gitignores review packets. Validator rejects opus/inherit agent defaults and long skill descriptions.

## [1.0.0] — 2026-11-10
### Added
- Rules template: workflow (no vibe coding), code quality, architecture (ports & adapters), security, TDD testing,
  path-scoped Kotlin/JVM, TypeScript, Python, SQL/migrations rules.
- Skills: `setup`, `bootstrap-project`, `tdd`, `reuse-first`, `interface-first-design`, `plan-change`,
  `secure-self-review`, `definition-of-done`, `pr-review`, `review-cycle`.
- Agents: `requirements-verifier`, `performance-reviewer`.
- `guard_secrets.py` PreToolUse hook: blocks secret-file access, hard-coded secrets, env dumps, force push, hard reset, git clean.
- Manifest-based installer with safe updates (`.eng-new` on local modifications), ignore file, dry run, user mode.
- CI: validation, shellcheck, pytest on Ubuntu + macOS, gitleaks.
