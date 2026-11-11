# claude-code-base

Engineering standards for Claude Code, packaged as a plugin marketplace so every project gets the same behaviour:
**no vibe coding, TDD, reuse before writing, interface-first design, no leaked secrets or backdoors, one ticket →
one reviewed PR, and every merge traceable to its GitHub issue.** Works with or without OpenSpec.

- [Quickstart](#quickstart)
- [Commands at a glance](#commands-at-a-glance)
- [Daily workflow](#daily-workflow)
- [Ticket tracking](#ticket-tracking)
- [Command reference](#command-reference)
- [Skills Claude uses automatically](#skills-claude-uses-automatically)
- [Reviewer agents](#reviewer-agents)
- [Review cycle in detail](#review-cycle-in-detail)
- [Rules](#rules)
- [Security guard](#security-guard)
- [Updating and versioning](#updating-and-versioning)
- [Recommended extras](#recommended-extras)
- [Token usage](#token-usage)
- [Developing this repo](#developing-this-repo)

---

## Quickstart

**1. Once per machine** — inside any Claude Code session:
```text
/plugin marketplace add ErickZarat/claude-code-base
/plugin install eng@claude-code-base                         # choose "user" scope → works in every project
/plugin install security-guidance@claude-plugins-official
```
Needs `gh auth login` (private repo, tickets, PRs). Type `/eng:` to confirm the commands appear.

**2. Once per project:**
```text
/eng:setup
```
Installs rules, CLAUDE.md, settings, pre-commit and the PR-title check, then fills CLAUDE.md for your stack. Commit it.

**3. Every feature:**
```text
/opsx:propose <what you want>   # plan → you approve proposal, specs and tasks
/eng:epic                       # GitHub epic + one ticket per task, tagged [ISSUE-n]
/eng:task next                  # ticket → branch → TDD → DoD → PR "[ISSUE-n] …" → review cycle → ready
  … you merge the PR …
/clear                          # fresh context for the next ticket
/eng:task next                  # repeat until the epic is done
/opsx:archive                   # when every ticket is merged
```
That's it. Everything below is reference.

---

## Commands at a glance

| Command | What it does |
|---|---|
| `/eng:setup` | Install / update the project files (rules, CLAUDE.md, settings, pre-commit, PR-title check) |
| `/eng:bootstrap` | Fill CLAUDE.md for this repo, prune unused language rules, optional OpenSpec |
| `/eng:epic [change]` | OpenSpec change → GitHub epic + linked ticket per task |
| `/eng:task <n\|next>` | One ticket end to end, ending in a reviewed, ready-for-review PR |
| `/eng:dod` | Definition-of-done check (build, tests, lint, diff, security) |
| `/eng:review [PR#]` | Review → fix → re-review cycle until merge-ready |
| `/eng:review-once [PR#]` | One read-only review round (e.g. someone else's PR) |

---

## Daily workflow

```
 Plan ─────────► Tickets ─────► Per ticket (/eng:task) ──────────────────────────────────────► Merge
 /opsx:propose    /eng:epic      branch → TDD → /eng:dod → draft PR [ISSUE-n] → /eng:review → ready   you
 (you approve)                   (one ticket = one branch = one PR; small diffs → quick, cheap reviews)
```

| Step | You do | Claude does |
|---|---|---|
| 1. Plan | Describe the change; approve proposal/specs/tasks | Reads the code, asks questions, writes the OpenSpec change. No code before approval |
| 2. Tickets | Run `/eng:epic`; confirm granularity | Creates the epic and one linked ticket per task, tags `tasks.md`, commits the mapping |
| 3. Work a ticket | Run `/eng:task next` | Branch, TDD per behaviour, reuse/interfaces, ticks the task, `/eng:dod`, draft PR, review cycle, marks PR ready, comments the verdict |
| 4. Decide | Answer escalations; read the PR | Stops and asks on repeated findings, blocked fixes, product decisions |
| 5. Merge | You merge (squash) | Never approves or merges |
| 6. Next | `/clear`, `/eng:task next` | Picks the next ticket that is open and has no PR |

No OpenSpec in a project? Describe the change, Claude writes a `plan-change` plan, then `/eng:dod` and
`/eng:review` on the PR. Title it `[NO-ISSUE] …` or create the issue by hand and use `[ISSUE-n]`.

---

## Ticket tracking

**Structure on GitHub**
```
[EPIC] Add refunds (add-refunds)            #42   label: epic   ← one per OpenSpec change
 ├─ 1.1 Add refunds table migration         #43   label: task   ← sub-issue, one per open task
 ├─ 2.1 POST /refunds endpoint              #44
 └─ 2.2 Reject refunds above order total    #45
```
The epic body has the proposal summary and a checklist of its tickets. Tasks already `[x]` get no ticket.
With `--group-by section`, each `## N.` section of `tasks.md` becomes one ticket (its tasks become a checklist).

**The tag `[ISSUE-<n>]` goes at the start of:**
| Where | Example |
|---|---|
| `tasks.md` (written by `/eng:epic`) | `- [ ] 2.1 [ISSUE-44] POST /refunds endpoint` |
| Branch name | `issue-44-post-refunds-endpoint` |
| Every commit | `[ISSUE-44] feat(refunds): add POST /refunds` |
| PR title | `[ISSUE-44] feat: POST /refunds endpoint` |
| PR body | `Closes #44` · `Part of #42` |
| Squash-merge commit on `main` | = PR title, so `git log --grep "ISSUE-44"` finds everything |

**What enforces it**
- `/eng:task` builds branch names and PR titles with the script, so they're always consistent.
- `.github/workflows/eng-pr-title.yml` (installed by `/eng:setup`) fails any PR whose title doesn't start with
  `[ISSUE-<n>] ` or `[NO-ISSUE] `. Dependabot/Renovate are exempt. Make it a required check in branch protection.
- `/eng:epic` offers the repo setting *squash merge, commit title = PR title* so merge commits keep the tag, and adds
  an autolink so `ISSUE-44` in commits and PRs links to issue #44 (both need repo admin).
- `openspec/changes/<change>/github.json` stores the change ↔ epic ↔ ticket mapping; re-running `/eng:epic`
  after editing `tasks.md` only creates tickets for new tasks.

---

## Command reference

All commands are plugin skills, invoked as `/eng:<name>`. Arguments are read by Claude, so plain language
works too ("work on ticket 44, thorough review").

### `/eng:setup`
Install or update the per-project files.
```text
/eng:setup               # install/update in the current repo (shows a dry run first)
/eng:setup --dry-run     # only show what would change
/eng:setup --user        # rules only, into ~/.claude (apply to every project on this machine)
```
- First run: creates `.claude/rules/`, `.claude/settings.json`, `CLAUDE.md`, `.pre-commit-config.yaml`,
  `.github/workflows/eng-pr-title.yml`, updates `.gitignore`, then runs `bootstrap`.
- Later runs: updates files you haven't modified; for ones you customised, writes `<file>.eng-new` and helps you merge.
- Never overwrites `CLAUDE.md` or `settings.json` (except renaming the old `eng-standards` plugin id to `eng`).

### `/eng:bootstrap`
Adapt the setup to the repo (runs automatically after the first `setup`). Detects the stack, fills every `TODO` in
CLAUDE.md with verified build/test/lint commands, prunes unused language rules (and records them in
`.claude/.eng-standards-ignore`), asks whether to use OpenSpec, creates `.env.example`.

### `/eng:epic`
OpenSpec change → GitHub epic + tickets.
```text
/eng:epic                          # the active change (asks if there are several)
/eng:epic add-refunds              # a specific change
/eng:epic add-refunds --group-by section   # one ticket per "## N." section instead of per task
/eng:epic --dry-run                # show what would be created
```
1. Checks `gh` auth, validates the change (`openspec validate`), confirms `tasks.md` is approved.
2. Suggests `--group-by section` when tasks are tiny or numerous (fewer tickets → fewer PRs).
3. Previews, creates epic + tickets + sub-issue links + labels (`epic`, `task`) + `ISSUE-` autolink.
4. Writes `[ISSUE-n]` into `tasks.md` and `github.json`; commits them (or leaves them for the first task PR if `main` is protected).
5. Offers the squash-merge repo setting. Idempotent: re-run after changing `tasks.md`.

### `/eng:task`
One ticket → one PR, with DoD and the review cycle every time.
```text
/eng:task next                     # next ticket: not done, still open, no PR yet
/eng:task 44                       # a specific ticket
/eng:task 44 --depth thorough      # force a deeper review (auth, payments, migrations…)
/eng:task 45 --stack               # build on an unmerged earlier ticket's branch
```
1. Clean working tree; one task per context (asks you to `/clear` otherwise).
2. Reads the ticket and only the OpenSpec parts it needs.
3. Branch `issue-<n>-<slug>` from the latest default branch (asks to wait or stack if it depends on an unmerged ticket).
4. TDD per behaviour, reuse-first, interfaces; ticks the task in `tasks.md`. Out-of-scope discoveries become proposed new tasks, not extra code.
5. `/eng:dod` — must pass.
6. `[ISSUE-n]` commits, push, **draft** PR titled `[ISSUE-n] <type>: <task>` with `Closes #n` / `Part of #epic`.
7. Review cycle on the PR (small task PRs → `quick`, 1 reviewer).
8. Clean exit → PR marked ready + one verdict comment. Escalation → stays draft with the open question. Never merges.

### `/eng:dod`
Run before saying a task is finished or opening a PR (`/eng:task` runs it for you).
Checks: build, tests, lint (real output) · diff only touches the task · no debug code/TODOs · reuse applied ·
interfaces for external deps · TDD followed · every requirement implemented · docs/.env.example updated ·
`secure-self-review` passed. Ends with a `Done / Changed / Verified / Security / Follow-ups` summary; failures go at the top.

### `/eng:review`
Iterative review → remediation → re-review until merge-ready (`/eng:task` runs it for you).
```text
/eng:review                       # current branch vs main
/eng:review 42                    # PR #42
/eng:review 42 --depth thorough   # depth of round 1 (default: triage decides)
/eng:review 42 --max-rounds 5     # default 3
```
See [Review cycle in detail](#review-cycle-in-detail).

### `/eng:review-once`
**One** read-only review round — reports findings, fixes nothing. For someone else's PR or a quick opinion.
```text
/eng:review-once 42                    # PR #42
/eng:review-once 42 --depth thorough   # quick | standard | thorough (default: triage decides)
```
1. Builds a **review packet** once (`scripts/review_packet.py`): diff, changed files, requirement sources, triage.
2. Deterministic gates first: build, tests, lint, gitleaks, semgrep (if installed).
3. Launches only the reviewers the change needs, in parallel, each reading the packet:

   | Depth | Reviewers | When |
   |---|---|---|
   | `quick` | `code-reviewer` (also checks requirements) | ≤ 50 changed lines, no security triggers |
   | `standard` | `requirements-verifier` + `code-reviewer` + `performance-reviewer` if triage flags data/loops/I/O | Default |
   | `thorough` | standard + performance always + dedicated security reviewer + pr-review-toolkit agents, on opus | Auth, payments, migrations, public APIs |
4. Confirms every 🔴/🟠 finding against the code; drops false positives.
5. Report (tables): gates, requirements traceability, findings with IDs and severity, verdict.
   Say "post it to the PR" to comment via `gh`.

### Planning commands (OpenSpec)
| Command | When |
|---|---|
| `/opsx:propose`, `/opsx:apply`, `/opsx:archive` | Projects with OpenSpec (`openspec init --tools claude`). Use `/eng:task` instead of `/opsx:apply` to get one PR per task |
| "plan this change" → `plan-change` skill | Projects without OpenSpec; plan in chat or `docs/plans/<date>-<slug>.md` |

---

## Skills Claude uses automatically

You don't need to call these; the rules and skill descriptions make Claude use them at the right moment.
You can still ask for them by name ("use the tdd skill", "run reuse-first for this").

| Skill | Triggers when | What it enforces |
|---|---|---|
| `tdd` | Implementing any feature, change or bug fix | One failing test (shown failing) → minimum code (shown passing) → refactor. Code written before its test is deleted |
| `reuse-first` | Before creating any function, class, DTO, constant, utility or dependency | Searches by intent and states `REUSE` / `EXTEND` / `EXTRACT` / `NEW` with a reason |
| `interface-first-design` | Adding anything external or replaceable (DB, cache, queue, API, storage, payments, clock…) | Port in the domain, adapter in infrastructure, DI wiring, fake + integration + contract tests |
| `plan-change` | Change bigger than one file, no `openspec/` folder | Goal, out of scope, approach, TDD-ordered steps, risks — then waits for approval |
| `secure-self-review` | Code touching input, auth, data, config, secrets, network, deps; always in done/review | gitleaks / semgrep / dependency audit if installed + manual checklist; HIGH/CRITICAL fixed before done |

---

## Reviewer agents

Read-only subagents with their own context, so they don't grade their own work. Used by `review-once` / `review`,
or directly: *"use the requirements-verifier agent on this branch"*. All read the shared review packet first and
answer with tables only.

| Agent | Default model | Role |
|---|---|---|
| `requirements-verifier` | sonnet (opus in thorough) | Requirement → code → test traceability |
| `code-reviewer` | sonnet (opus in thorough) | Security, tests, correctness, architecture, readability in one pass |
| `performance-reviewer` | sonnet | Efficiency at expected scale — only when triage flags it |
| `fix-verifier` | haiku | Re-review rounds: verifies fixes against the remediation diff, flags regressions |

### `requirements-verifier`
- Collects requirements from the OpenSpec change (proposal, tasks, every scenario), `docs/plans/`, PR body, linked issues.
- Builds a table **requirement → code (file:line) → test** with status ✅ Done · ⚠️ Partial · ❌ Missing · 🐞 Wrong · 🧪 Untested.
- Lists unchecked tasks and **scope creep** (changed code that maps to no requirement).
- Checks each requirement has a test that would fail without the code.

### `code-reviewer`
- One pass over security (secrets, backdoors, injection, authz, dependencies), tests (missing, weak, flaky),
  correctness (silent failures, edge cases), architecture (interfaces, no duplication) and readability.
- Doesn't repeat what lint / gitleaks / semgrep already reported. Max 15 findings.

### `fix-verifier`
- VERIFY rounds only. Marks each FIXED finding VERIFIED or REOPENED from the remediation diff, flags regressions.
- Escalates to a TARGETED round if a fix changed requirement-level behaviour.

### `performance-reviewer`
- Algorithms: O(n²) lookups, repeated work in loops.
- Database: N+1, `SELECT *`, missing pagination/indexes, long transactions, ClickHouse/Timescale key alignment, row-by-row inserts.
- I/O & concurrency: remote calls in loops, blocking in coroutines/event loops, missing timeouts, unbounded caches/queues.
- Resources: unclosed streams/connections, retained large objects.
- Each finding: severity, location, impact at expected scale, fix; suggests `EXPLAIN` / benchmarks when it can't prove it.

---

## Review cycle in detail

```
Round 1  FULL review ──► findings ──► ledger
   ▼
Remediation  fixes with TDD, answers questions, declines minors with reasons
   ▼
Next round scope by highest severity fixed:  🔴 → FULL   🟠 → TARGETED   🟡/💡/❓ → VERIFY
   (later rounds read only the remediation diff; build + tests run in EVERY round)
   ▼
Exit when all criteria hold — or stop and ask you
```

### Severity
| Severity | Examples | To exit |
|---|---|---|
| 🔴 BLOCKER | Failing build/tests, missing or wrong requirement, **missing tests**, TDD skipped, vulnerability, leaked secret | Fixed |
| 🟠 MAJOR | Edge-case bug, real performance problem, concrete dependency in domain, duplicated logic, silent failure | Fixed |
| 🟡 MINOR | Naming, comments, small inefficiency | Fixed or declined with reason |
| 💡 SUGGESTION | Optional improvement | Accepted or declined with reason |
| ❓ QUESTION | Reviewer needs clarification | Answered (becomes a finding if it reveals a problem) |

### Round cost
| Scope | Reviewers | Reads |
|---|---|---|
| FULL | Same set as round 1 (by depth) | Whole change |
| TARGETED | `requirements-verifier` + reviewers for the affected areas | Remediation diff |
| VERIFY | `fix-verifier` (haiku) | Remediation diff + ledger |

### Roles
- **Reviewers** — fresh subagents each round; raise findings, verify previous fixes (VERIFIED / REOPENED), never edit code.
- **Author** — your session; fixes in order 🔴 → 🟠 → ❓ → 🟡 → 💡, bugs via a failing test first, commits as
  `fix(review): R1-3 …`. It cannot verify its own fixes.

### Exit criteria
- Build, full tests, lint green on the final commit.
- Latest requirements check: every requirement ✅ Done (no Missing / Partial / Wrong / Untested), no fix escalated since.
- No open or reopened 🔴, 🟠 or ❓; every 🟡 verified or declined with a reason.
- Every fix from the last remediation verified by a reviewer.

### When it stops and asks you
- Max rounds reached (default 3).
- A finding's fingerprint (component · problem class) seen a 3rd time — variants of the same problem count.
  On the 2nd time the author must fix the root cause across all variants, not just the reported example.
- A hook, permission or tool error blocks the same fix twice (Claude never rewords content to get past a guard).
- Author disagrees with a 🔴/🟠 finding.
- A question needs a product/business decision.

### The ledger
`openspec/changes/<change>/reviews/<branch>/ledger.md` (OpenSpec) or `.reviews/<branch>/ledger.md`. One table per round with
stable IDs (`R1-3`), a fingerprint and `Seen` count per finding, and statuses
`OPEN → FIXED → VERIFIED / REOPENED · DECLINED · ANSWERED`. Commit it as the PR's
audit trail, or add `.reviews/` to `.gitignore`.

### Final report
```
Review cycle complete — 3 rounds — verdict: READY TO MERGE
Findings: 14 raised · 10 fixed · 3 declined · 1 answered
Ledger: .reviews/feature-refunds/ledger.md
```

---

## Rules

Installed into `.claude/rules/` and loaded automatically every session.

| File | Covers |
|---|---|
| `workflow.md` | Read before editing, ask when unclear, plan first, TDD, small steps, no placeholders, never fake success, git hygiene |
| `code-quality.md` | Descriptive names, comments explain *why*, small functions, DRY, error handling, structured logging, efficiency |
| `architecture.md` | Depend on interfaces (ports), adapters in infrastructure, constructor DI, layering, validated config |
| `security.md` | No hard-coded secrets, no backdoors, input validation, parameterized SQL, server-side authz, dependency hygiene |
| `testing.md` | TDD mandatory, behaviour tests, fakes for ports, Testcontainers, deterministic, never weaken tests |
| `lang/kotlin-jvm.md` | `*.kt`, `*.kts`, `*.java` — Kotlin/Java, Spring Boot, Ktor, gRPC, JDBC, coroutines |
| `lang/typescript.md` | `*.ts`, `*.tsx`, `*.js` — strict TS, runtime validation, frontend secret exposure |
| `lang/python.md` | `*.py` — types, Protocols, safe subprocess/deserialization |
| `lang/sql-migrations.md` | `*.sql`, migrations — forward-only, zero-downtime, indexes |

Language rules only load when Claude touches matching files. Opt out of one per project by listing it in
`.claude/.eng-standards-ignore`. Customise any rule freely; updates won't overwrite your edits.

---

## Security guard

Five layers, from fastest to last line of defence:

1. **Rules** — Claude's intent (`security.md`).
2. **`guard_secrets.py` hook** (from the plugin, runs before every Read/Write/Edit/Bash) — blocks:
   reading/editing `.env*` (not `.env.example`), keys, `~/.ssh`, `~/.aws`, credential JSONs · writing AWS/GitHub/Slack/
   Stripe/Google/Anthropic/OpenAI keys, JWTs, private keys, `password = "literal"`, `user:pass@host` URLs ·
   `printenv`, `git push --force`, `git reset --hard`, `git clean -f`, `rm -rf /`.
3. **Permission deny-list** in `.claude/settings.json`.
4. **security-guidance plugin** — model review of changes in-session.
5. **gitleaks** — pre-commit hook (`pre-commit install`) and in CI.

In **test files** (`src/test/`, `*Test.kt`, `*.spec.ts`, `test_*.py`, `*_test.go`, …) only real token formats are
blocked; `password = "…"` and `user:pass@host` style fakes are allowed so you can test credential handling.
Values containing `fake`, `mock`, `test` or `sample` count as placeholders everywhere. Anything else that's a
deliberate fake: add `pragma: allowlist secret` on that line. Block messages show the line with the secret redacted.

---

## Updating and versioning

**Publishing a change (this repo):** edit → tests green → bump `version` in
`plugins/eng/.claude-plugin/plugin.json` → `CHANGELOG.md` entry → push → tag `vX.Y.Z`.

**Receiving it:**
```text
/plugin marketplace update claude-code-base   # skills, agents, hook update immediately
/eng:setup                          # in each project, to sync rules
```
| File state in the project | What `setup` does |
|---|---|
| Rule you never touched | Updated |
| Rule you customised | Kept; new version written as `<file>.eng-new` for you to merge |
| `CLAUDE.md`, `settings.json` | Never touched after first install |
| Listed in `.claude/.eng-standards-ignore` | Never installed |

Installed version: `.claude/.eng-standards-version`. Without the plugin: `git clone` this repo and run
`./install.sh /path/to/project` (`--user`, `--dry-run` also work).

---

## Recommended extras

```text
/plugin install pr-review-toolkit@claude-plugins-official   # code-quality reviewers used by review-once
/plugin install code-review@claude-plugins-official
/plugin marketplace add trailofbits/skills                  # semgrep, supply-chain-risk-auditor, ...
```
CLI tools the security review uses when present: `gitleaks`, `semgrep`, `osv-scanner`, `gh` (PR numbers).
OpenSpec: `npm install -g @fission-ai/openspec@latest && openspec init --tools claude`.
Use one planning system per project: OpenSpec **or** superpowers, not both.

---

## Token usage

Reviews are the expensive part: every reviewer subagent is a separate context. What's built in:

| Lever | How |
|---|---|
| Fewer reviewers | Triage launches only what the diff needs; `quick` = 1 reviewer, `standard` = 2–3 |
| Cheaper models | Reviewers on sonnet, fix verification on haiku; opus only with `--depth thorough` |
| Read once | One review packet per round instead of each reviewer exploring the repo |
| Tools before AI | Build/tests/lint/gitleaks/semgrep run first; reviewers don't repeat them |
| Smaller re-reviews | Later rounds read only the remediation diff; max 3 rounds |
| Small always-on cost | Review skills are manual-only; all descriptions are short |

Your habits matter as much:
- **`/clear` between tasks** — a long session re-sends its whole history on every request. Start each review in a fresh session.
- **Disable skills/plugins you don't use** in `/plugin` — every enabled skill's description is sent on every request.
- **Pick the depth on purpose:** `quick` for small fixes, `thorough` only for risky changes.
- Check what a review cost with `/cost` (or the usage view) and compare depths.

---

## Developing this repo

See `CLAUDE.md`. Quick check:
```bash
python3 scripts/validate.py && shellcheck install.sh plugins/eng/install.sh && pytest -q
claude --plugin-dir ./plugins/eng   # try plugin changes locally
```
