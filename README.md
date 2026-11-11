# claude-code-base

Engineering standards for Claude Code, packaged as a plugin marketplace so every project gets the same behaviour:
**no vibe coding, TDD, reuse before writing, interface-first design, no leaked secrets or backdoors, and iterative
PR review until every requirement is implemented and tested.** Works with or without OpenSpec.

- [Quickstart](#quickstart)
- [Daily workflow](#daily-workflow)
- [Command reference](#command-reference)
- [Skills Claude uses automatically](#skills-claude-uses-automatically)
- [Reviewer agents](#reviewer-agents)
- [Review cycle in detail](#review-cycle-in-detail)
- [Rules](#rules)
- [Security guard](#security-guard)
- [Updating and versioning](#updating-and-versioning)
- [Recommended extras](#recommended-extras)
- [Developing this repo](#developing-this-repo)

---

## Quickstart

**1. Once per machine** — inside any Claude Code session:
```text
/plugin marketplace add ErickZarat/claude-code-base
/plugin install eng-standards@claude-code-base          # choose "user" scope → works in every project
/plugin install security-guidance@claude-plugins-official
/plugin install pr-review-toolkit@claude-plugins-official   # optional, improves code-quality review
```
Private repo: Claude Code fetches it with your git credentials (`gh auth login` or SSH). Type `/eng-standards:` to
confirm the commands appear.

**2. Once per project** — open Claude Code in the repo:
```text
/eng-standards:setup
```
Previews, installs rules + CLAUDE.md + settings + pre-commit, then fills CLAUDE.md for your stack. Commit the result.

**3. Every change:**
```text
/opsx:propose <what you want>        # or just describe it — Claude uses plan-change if there is no OpenSpec
  … approve the plan, Claude implements with TDD …
/eng-standards:definition-of-done    # self-check before the PR
/eng-standards:review-cycle 42       # review → fix → re-review until merge-ready (42 = PR number)
```
That's it. Everything below is reference.

---

## Daily workflow

```
 Plan ───────────► Implement (TDD) ───────► Done check ─────────► Review cycle ──────────► Merge
 /opsx:propose      tdd, reuse-first,        /eng-standards:        /eng-standards:          you
 or plan-change     interface-first-design   definition-of-done     review-cycle <PR#>
 (you approve)      (automatic via rules)                           (stops to ask when needed)
```

| Step | You do | Claude does |
|---|---|---|
| 1. Plan | Describe the change; approve the plan | Reads the code, asks questions, writes an OpenSpec change or a `plan-change` plan. No code before approval |
| 2. Implement | Watch / answer questions | Red → green → refactor per behaviour, searches for reusable code first, puts external dependencies behind interfaces |
| 3. Done check | Run `/eng-standards:definition-of-done` | Build, tests, lint, diff review, security self-review, honest summary |
| 4. PR | Open the PR (or ask Claude: "commit and open a PR") | — |
| 5. Review | Run `/eng-standards:review-cycle <PR#>` | Review rounds with independent reviewers, fixes findings with TDD, re-reviews by severity, writes a ledger |
| 6. Decide | Answer escalated questions; read the verdict | Posts the report to the PR only if you ask |
| 7. Merge | You merge | Never approves or merges |

---

## Command reference

All commands are plugin skills, invoked as `/eng-standards:<name>`. Arguments are read by Claude, so plain language
works too ("review PR 42, max 3 rounds").

### `/eng-standards:setup`
Install or update the per-project files.
```text
/eng-standards:setup               # install/update in the current repo (shows a dry run first)
/eng-standards:setup --dry-run     # only show what would change
/eng-standards:setup --user        # rules only, into ~/.claude (apply to every project on this machine)
```
- First run: creates `.claude/rules/`, `.claude/settings.json`, `CLAUDE.md`, `.pre-commit-config.yaml`, updates `.gitignore`,
  then runs `bootstrap-project`.
- Later runs: updates rules you haven't modified; for rules you customised, writes `<file>.eng-new` and helps you merge.
- Never overwrites `CLAUDE.md` or `settings.json`.

### `/eng-standards:bootstrap-project`
Adapt the setup to the repo (runs automatically after the first `setup`). Detects the stack, fills every `TODO` in
CLAUDE.md with verified build/test/lint commands, prunes unused language rules (and records them in
`.claude/.eng-standards-ignore`), asks whether to use OpenSpec, creates `.env.example`.

### `/eng-standards:definition-of-done`
Run before saying a task is finished or opening a PR.
```text
/eng-standards:definition-of-done
```
Checks: build, tests, lint (real output) · diff only touches the task · no debug code/TODOs · reuse applied ·
interfaces for external deps · TDD followed · every requirement implemented · docs/.env.example updated ·
`secure-self-review` passed. Ends with a `Done / Changed / Verified / Security / Follow-ups` summary; failures go at the top.

### `/eng-standards:pr-review`
**One** review round. Reports findings; does not fix anything.
```text
/eng-standards:pr-review                       # current branch vs main
/eng-standards:pr-review 42                    # PR #42 (needs gh)
/eng-standards:pr-review develop               # current branch vs develop
/eng-standards:pr-review 42 --scope TARGETED   # FULL (default) | TARGETED | VERIFY
```
1. Gates: build, full test suite, lint.
2. Four reviewers in parallel, each in a fresh context: `requirements-verifier`, `performance-reviewer`,
   security (`secure-self-review`), code quality (`pr-review-toolkit` agents if installed, otherwise your rules).
3. Verifies every 🔴/🟠 finding against the code; drops false positives.
4. Report: gates, requirements traceability table, findings with IDs and severity, verdict
   (✅ APPROVE · 🟠 APPROVE WITH COMMENTS · ❌ REQUEST CHANGES).

Use it when you only want an opinion, e.g. on someone else's PR. Say "post it to the PR" to comment via `gh`.

### `/eng-standards:review-cycle`
Iterative review → remediation → re-review until merge-ready. **This is the one to use on your own PRs.**
```text
/eng-standards:review-cycle                    # current branch vs main
/eng-standards:review-cycle 42                 # PR #42
/eng-standards:review-cycle 42 --max-rounds 3  # default 5
```
See [Review cycle in detail](#review-cycle-in-detail).

### Planning commands
| Command | When |
|---|---|
| `/opsx:propose`, `/opsx:apply`, `/opsx:archive` | Projects with OpenSpec (installed by `openspec init --tools claude`) |
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

Read-only subagents with their own context, so they don't grade their own work. Used by `pr-review` / `review-cycle`,
or directly: *"use the requirements-verifier agent on this branch"*.

### `requirements-verifier`
- Collects requirements from the OpenSpec change (proposal, tasks, every scenario), `docs/plans/`, PR body, linked issues.
- Builds a table **requirement → code (file:line) → test** with status ✅ Done · ⚠️ Partial · ❌ Missing · 🐞 Wrong · 🧪 Untested.
- Lists unchecked tasks and **scope creep** (changed code that maps to no requirement).
- Checks each requirement has a test that would fail without the code.

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
   (requirements + test coverage are checked in EVERY round)
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

### Roles
- **Reviewers** — fresh subagents each round; raise findings, verify previous fixes (VERIFIED / REOPENED), never edit code.
- **Author** — your session; fixes in order 🔴 → 🟠 → ❓ → 🟡 → 💡, bugs via a failing test first, commits as
  `fix(review): R1-3 …`. It cannot verify its own fixes.

### Exit criteria
- Build, full tests, lint green on the final commit.
- Every requirement ✅ Done (no Missing / Partial / Wrong / Untested).
- No open or reopened 🔴, 🟠 or ❓; every 🟡 verified or declined with a reason.
- Every fix from the last remediation verified by a reviewer.

### When it stops and asks you
- Max rounds reached (default 5).
- Same finding reopened twice.
- Author disagrees with a 🔴/🟠 finding.
- A question needs a product/business decision.

### The ledger
`openspec/changes/<change>/reviews/ledger.md` (OpenSpec) or `.reviews/<branch>/ledger.md`. One table per round with
stable IDs (`R1-3`) and statuses `OPEN → FIXED → VERIFIED / REOPENED · DECLINED · ANSWERED`. Commit it as the PR's
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

False positive on a deliberate fake value in a test? Add `pragma: allowlist secret` on that line.

---

## Updating and versioning

**Publishing a change (this repo):** edit → tests green → bump `version` in
`plugins/eng-standards/.claude-plugin/plugin.json` → `CHANGELOG.md` entry → push → tag `vX.Y.Z`.

**Receiving it:**
```text
/plugin marketplace update claude-code-base   # skills, agents, hook update immediately
/eng-standards:setup                          # in each project, to sync rules
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
/plugin install pr-review-toolkit@claude-plugins-official   # code-quality reviewers used by pr-review
/plugin install code-review@claude-plugins-official
/plugin marketplace add trailofbits/skills                  # semgrep, supply-chain-risk-auditor, ...
```
CLI tools the security review uses when present: `gitleaks`, `semgrep`, `osv-scanner`, `gh` (PR numbers).
OpenSpec: `npm install -g @fission-ai/openspec@latest && openspec init --tools claude`.
Use one planning system per project: OpenSpec **or** superpowers, not both.

---

## Developing this repo

See `CLAUDE.md`. Quick check:
```bash
python3 scripts/validate.py && shellcheck install.sh plugins/eng-standards/install.sh && pytest -q
claude --plugin-dir ./plugins/eng-standards   # try plugin changes locally
```
