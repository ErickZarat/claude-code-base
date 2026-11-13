# Changelog

All notable changes to the `eng-standards` plugin. Versions follow semver; the version lives in
`plugins/eng-standards/.claude-plugin/plugin.json`.

## [3.2.0] — 2026-11-13
### Changed — remediation fixes the cause, not the flagged line
- Every chosen BLOCKER/MAJOR gets a **fix brief** in the ledger before any edit: failing scenario, root cause, same
  problem class elsewhere, one fix site, and two tests (reviewer's scenario + a variant) shown failing first.
  A finding seen twice also records why the previous fix missed.
- New `scripts/fix_brief_check.py <ledger>`: exits 1 for any fixed BLK/MAJ without a complete brief; part of the
  single-round exit criteria.
- code, security and performance reviewers state a concrete failing scenario (`when … → …; expected …`) for every
  BLK/MAJ, so the author has something testable.

## [3.1.0] — 2026-11-12
### Added — companion plugins
- The project template enables **ponytail** (`ponytail@ponytail`, least code that works) and **pstack**
  (`pstack@cursor-plugins`, debugging/explaining skills) for every contributor via `.claude/settings.json`.
  `/eng:setup` offers to add them to an existing `settings.json`.
- Workflow rule: where ponytail/pstack disagree with eng, eng wins (TDD for every behaviour, ports are required
  structure, doc comments on public APIs); pstack's multi-agent skills only on request.
### Removed — duplicated by ponytail
- `reuse-first` skill and the code-quality lines it duplicated (search before writing, no premature abstraction,
  why-not-how comments).
### Changed
- Template CLAUDE.md non-negotiables: least code (ponytail) and the single review round.
### Migration
- Re-run `/eng:setup` and accept the `settings.json` additions (or install both plugins at user scope). Needs `node`.

## [3.0.0] — 2026-11-11
### Changed — one PR per section, one review round per PR (≈ a fraction of the review tokens)
- **`/eng:epic` default granularity is now a `## N.` section of `tasks.md`**: one ticket = one branch = one PR; the
  section's tasks become the ticket checklist and the PR's commits (`[TASK-50] feat(x): <task> (1.2)`). Cross-section
  `after:` becomes the section ticket's "blocked by". `--group-by task` keeps the old per-task tickets.
- `spec_lint` prints a **PR plan** (one PR per section) and warns when sections form a single chain.
- Sync ticks every task of a closed section ticket in `tasks.md`.
- **`/eng:review` runs one round by default** (`--max-rounds 1`): every reviewer → checkpoint → fix the chosen findings
  → confirm with build/tests/lint + self-check (`FIXED (self-verified)`), no second AI round. 🔴/🟠 you choose not
  to fix stay OPEN and are listed under the PR's *Pending decisions*. Reviewers are unchanged (as strict as before).
- `/eng:task` works a section ticket task by task (TDD + one commit each) and runs one review round.
- OpenSpec `[eng]` tasks rules: one section = one PR-sized deliverable; tasks inside are commits.
- PR template DoD line and the workflow rule reflect the single round.
### Migration
- Changes already synced keep their granularity (`github.json` has items → per task). New changes default to
  sections; pass `--group-by task` to keep per-task PRs.
- Want the old cycle? `/eng:review --max-rounds 3`.
- Re-run `/eng:setup` to get the updated PR template, workflow rule and CLAUDE.md, and re-merge the `[eng]` rules into
  `openspec/config.yaml`.

## [2.10.0] — 2026-11-11
### Added — get it right the first time (fewer review rounds, fewer tokens)
- `checklists/self-check.md`: the reviewers' checklist for authors; `tests/test_review_coverage.py` keeps it in sync
  with every review topic (incl. SQL injection details).
- `self-check` skill: gates → packet hints (dynamic SQL, contracts) → walk the own diff against the checklist → fix.
  `/eng:dod` runs it (and no longer duplicates the security checklist).
- `/eng:task` **plan step** before the first test: files, reuse, reference pattern, ports, tests incl. edge cases,
  NFR targets, open questions.
- `/eng:bootstrap`: static analysis setup (detekt/ktlint, ESLint strict, ruff, semgrep packs) and a *Patterns*
  section in CLAUDE.md with canonical files to copy.
- `/eng:retro`: first-time-quality metrics (rounds per PR, clean first rounds, first-round findings per 100 changed
  lines); suggests lint/semgrep rules for lintable recurring findings. Ledger round headers record `changed lines`.
Reviewers are unchanged (as strict as before).

## [2.9.0] — 2026-11-11
### Added — working as a team
- **Spec-time dependencies:** `/eng:spec` reviews task dependencies (what must be merged first) and the lint prints a
  **Plan** — dependency levels, critical path, max parallel — warning when tasks form a single chain.
- **Native GitHub "blocked by" links** from `tasks.md` `after:` (with `Depends on #n` fallback); re-sync adds
  dependencies planned later.
- **`block`**: dependencies discovered while working are recorded on GitHub only (no `tasks.md` edit).
- **Claim:** `/eng:task` assigns the ticket before branching and refuses tickets assigned to others; `next` resumes
  my claims first and skips others', open-PR and blocked tickets.
- **`/eng:status`** board: done · in review · in progress · blocked (by what) · ready, with unblock hints.
### Changed
- Task PRs no longer tick `tasks.md` (parallel PRs conflicted on it); sync ticks tasks whose ticket is closed.

## [2.8.0] — 2026-11-11
### Added — spec-driven extras on top of OpenSpec (lightweight: scripts and CI, AI only at checkpoints)
1. **Spec lint** (`spec_lint.py`, `/eng:spec`): structure errors, vague wording, missing error cases, uncovered
   requirements, missing NFR section, task dependency cycles, oversized tasks; ≤10 ambiguity questions;
   `/eng:epic` stops on ERRORs.
2. **API contract check**: template CI `eng-contracts.yml` + `eng_contract_check.py` — `buf breaking` for .proto,
   `oasdiff breaking` for OpenAPI (Docker images), GraphQL/Avro flagged; override with
   `Breaking-change: approved — <reason>` in the PR body. Review packet lists *Contract changes*; architecture rule.
3. **Non-functional requirements**: OpenSpec rule for a *Non-functional requirements* section; lint warns; performance
   and security reviewers verify against it.
4. **Scenario ↔ test traceability** (`trace.py`): scenario IDs, `spec:` markers in tests, untested/stale report;
   `/eng:spec --before-archive` gate; reviewers report untested scenarios; tdd/testing rule updated.
5. **Decision records** (`decisions.py`, `decision` skill): `docs/decisions/NNNN-title.md` with supersede chains.
6. **Retro** (`findings_report.py`, `/eng:retro`): recurring review problem classes → proposed rules in
   `.claude/rules/learned.md`.
7. **Lite path** in `/eng:task` for tickets outside an OpenSpec change; `/eng:task new "title" --bug|--feature`.
8. **Task dependencies and size**: `(after: 1.1; size: S)` → "Depends on #n", `size:` labels; `next` waits for
   dependencies and lists blocked tickets.
- `openspec/config-rules.yaml`: `[eng]` rules merged into projects' `openspec/config.yaml` by bootstrap/setup.
- Coverage test: reviewers must check NFRs, contract compatibility and traceability.

Run `/eng:setup` in each project (new CI check, rules, OpenSpec rules merge).

## [2.7.0] — 2026-11-11
### Changed — ticket tags follow the issue type
- Tag format `[<KIND>-<n>]`. KIND = the issue's native type (organization repos: Bug → BUG, Feature → FEATURE,
  Task → TASK, custom types e.g. Spike → SPIKE), else a type label (bug → BUG, feature/enhancement → FEATURE,
  story → STORY, spike → SPIKE, chore → CHORE, task → TASK), else the default `ISSUE`.
- Branches follow the kind: `bug-10-null-total`, `task-44-post-refunds-endpoint`.
- `/eng:epic` tickets carry the `task` label → new `tasks.md` tags are `[TASK-n]`. Existing `[ISSUE-n]` tags are still
  recognised by sync, `next`, the PR title check and the PR checklist — no migration needed.
- `github_sync.py tag --issue <n>` prints the tag; `branch`/`title` look the kind up automatically (`--kind` to override).
- Autolinks for ISSUE-, TASK-, BUG-, FEATURE-, STORY-, CHORE-, SPIKE-.
- PR title check accepts any `[<KIND>-<n>]`; PR checklist fails when the title tag's number differs from `Closes #n`.
  Run `/eng:setup` in each project to update the CI checks, rule and PR template.

## [2.6.0] — 2026-11-11
### Fixed — secret guard false positives (reported from a project review: "key", "credentials", "secrets")
- Shell commands are parsed into program + arguments. Only arguments of programs that read file contents (`cat`,
  `less`, `cp`, `base64`, `source`, grep's file arguments, `< file`…) count as file reads; other commands are only
  checked for explicit secret file paths. `grep -rn "credentials" src/`, `kubectl get secrets`, `--set auth.key=…`,
  commit messages mentioning keys are allowed; `cat .env`, `cat ~/.aws/credentials`, `less server.key`,
  `base64 k8s/secrets/db.yaml` stay blocked.
- Source code inside a folder named `secrets/` (e.g. `com/acme/secrets/SecretService.kt`) is no longer treated as a
  secret file. Template `settings.json` drops the matching `Read(**/secrets/**)` deny rule — **existing projects:
  remove that line from `.claude/settings.json` by hand** (settings are project-owned and never overwritten).

### Added — SQL injection
- Review packet lists **Dynamic SQL candidates**: added lines that splice values into SQL (Kotlin/JS templates,
  concatenation, f-strings, `%`, `.format`, `sprintf`), with file:line.
- `security-reviewer` and `code-reviewer` (quick mode) have a concrete SQL injection checklist: bound parameters only,
  allowlisted identifiers (ORDER BY/columns/tables), LIKE escaping, IN lists, native-query escape hatches (JPA native,
  JdbcTemplate, jOOQ `DSL.field(String)`, Exposed `exec`, MyBatis `${}`, raw ClickHouse/Timescale SQL), stored
  procedures with dynamic SQL, second-order injection. Unparameterized value → BLK. Coverage test enforces it.
- Rules `security.md` and `lang/kotlin-jvm.md`: no string templates in SQL, allowlisted identifiers, LIKE escaping.

## [2.5.0] — 2026-11-11
### Changed — every review runs every dedicated reviewer again (as in 1.0)
- Default depth is `standard` for every PR, small ones included: `requirements-verifier`, `performance-reviewer`,
  the new dedicated `security-reviewer`, `code-reviewer`, and every installed pr-review-toolkit review agent.
  Triage no longer skips reviewers or picks `quick`; it only adds focus hints.
- `thorough` = the same reviewers on opus. `quick` (single combined reviewer) only when the user explicitly asks.
- `requirements-verifier` runs in every review-cycle round again (TARGETED and VERIFY included).
- New agent `security-reviewer` (sonnet): full security checklist incl. XSS, SSRF, open redirects, token handling,
  IAM/Docker/CI/Terraform in the diff.
- Template CLAUDE.md: `Minimum review depth: standard`.
- Kept from the token work (none of it removes a reviewer): shared review packet, deterministic gates first,
  sonnet default model, user checkpoint after each round.
- Coverage test now also requires standard/thorough to run all four dedicated reviewers.

## [2.4.0] — 2026-11-11
### Fixed — review coverage lost when reviewers were merged in 1.1.0
- Removed the per-reviewer finding caps (15 / 10) that could silently drop findings on large PRs.
- `code-reviewer` again covers the full secure-self-review checklist (PII in logs, generic client errors, CORS with
  credentials, outbound calls/telemetry, `.env.example`, path traversal, password hashing/crypto), plus the former
  pr-review-toolkit areas: stale comments, type design/encapsulation, needless complexity.
- Quick depth: `code-reviewer` now checks requirements/acceptance criteria itself (requirement → code → test) and
  does an efficiency pass (N+1, remote calls in loops, pagination, timeouts) when the dedicated reviewers don't run.
- TDD evidence (production code committed before its test) restored in `requirements-verifier` and `code-reviewer`.
- New `tests/test_review_coverage.py`: every review depth must cover every check the original review had — merging or
  trimming reviewers can no longer drop a check without a failing test.

## [2.3.0] — 2026-11-11
### Fixed
- The review cycle no longer starts fixing on its own. After **every** round it shows the full findings table and
  asks: fix required (BLK/MAJ/Q) · fix required + minors · choose IDs · stop. Nothing is edited until you answer;
  the decision is recorded in the ledger. `--auto` restores unattended behaviour (only when asked).
  `/eng:task` pauses at the same checkpoints; `/eng:review-once` asks before fixing.

### Added
- **Coverage** section in every review report: depth and why, reviewers run (with model), reviewers skipped and why,
  files reviewed vs changed, what was not checked, and the deeper option.
- `Minimum review depth: quick|standard|thorough` in the project's CLAUDE.md — reviews never go below it
  (enforced by `review_packet.py`). New projects get the line (default `quick`); existing projects can add it.

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
