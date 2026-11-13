# claude-code-base

Engineering standards for Claude Code, packaged as a plugin marketplace so every project gets the same behaviour:
**no vibe coding, TDD, reuse before writing, interface-first design, no leaked secrets or backdoors, one ticket →
one reviewed PR, and every merge traceable to its GitHub issue.** Works with or without OpenSpec.

- [Quickstart](#quickstart)
- [Commands at a glance](#commands-at-a-glance)
- [Daily workflow](#daily-workflow)
- [Ticket tracking](#ticket-tracking)
- [Working as a team](#working-as-a-team)
- [Getting it right the first time](#getting-it-right-the-first-time)
- [Spec-driven extras (on top of OpenSpec)](#spec-driven-extras-on-top-of-openspec)
- [Command reference](#command-reference)
- [Skills Claude uses automatically](#skills-claude-uses-automatically)
- [Companion plugins: ponytail and pstack](#companion-plugins-ponytail-and-pstack)
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
/plugin marketplace add DietrichGebert/ponytail      # companion: least code that works
/plugin install ponytail@ponytail
/plugin marketplace add cursor/plugins               # companion: pstack (debug, explain, unslop)
/plugin install pstack@cursor-plugins
```
Projects set up with `/eng:setup` also enable ponytail and pstack for every teammate (`.claude/settings.json`).
ponytail's hooks need `node` on PATH. Needs `gh auth login` (private repo, tickets, PRs). Type `/eng:` to confirm the commands appear.

**2. Once per project:**
```text
/eng:setup
```
Installs rules, CLAUDE.md, settings, pre-commit and the PR-title check, then fills CLAUDE.md for your stack. Commit it.

**3. Every feature:**
```text
/opsx:propose <what you want>   # plan → proposal, specs, design, tasks
/eng:spec                       # spec lint + questions → you approve the change
/eng:epic                       # GitHub milestone + one ticket per tasks.md section, tagged [TASK-n]
/eng:task next                  # ticket → branch → TDD → DoD → PR "[TASK-n] …" with checklists → review → ready
  … you merge the PR …
/clear                          # fresh context for the next ticket
/eng:task next                  # repeat until the epic is done
/eng:spec --before-archive      # every scenario has a test, every ticket closed
/opsx:archive                   # archive the change
```
Bugs and small fixes skip OpenSpec: `/eng:task new "Null total crashes refunds" --bug` (or `/eng:task <issue#>`).
That's it. Everything below is reference.

---

## Commands at a glance

| Command | What it does |
|---|---|
| `/eng:setup` | Install / update the project files (rules, CLAUDE.md, settings, pre-commit, PR-title check) |
| `/eng:bootstrap` | Fill CLAUDE.md for this repo, prune unused language rules, optional OpenSpec |
| `/eng:spec [change] [--before-archive]` | Spec lint + ambiguity questions before coding; traceability gate before archive |
| `/eng:retro` | Recurring review findings → proposed one-line rules in `.claude/rules/learned.md` |
| `/eng:epic [change]` | OpenSpec change → GitHub milestone (or parent issue) + one ticket per `## N.` section |
| `/eng:task <n\|next\|new "title" --bug>` | Claims one ticket and takes it end to end, ending in a reviewed, ready-for-review PR |
| `/eng:status [change]` | Team board: who is on which ticket, in review, blocked (by what), ready |
| `/eng:dod` | Definition-of-done check (build, tests, lint, diff, security) |
| `/eng:review [PR#]` | One review round (all reviewers) → checkpoint → fix chosen findings → gates + self-check. `--max-rounds N` for re-review rounds |
| `/eng:review-once [PR#]` | One read-only review round (e.g. someone else's PR) |

---

## Daily workflow

```
 Plan ─────────► Tickets ─────► Per ticket (/eng:task) ──────────────────────────────────────► Merge
 /opsx:propose    /eng:epic      branch → TDD → /eng:dod → draft PR [KIND-n] → /eng:review → ready    you
 (you approve)                   (one ticket = one branch = one PR; every PR gets every reviewer)
```

| Step | You do | Claude does |
|---|---|---|
| 1. Plan | Describe the change; approve proposal/specs/tasks | Reads the code, asks questions, writes the OpenSpec change. No code before approval |
| 2. Tickets | Run `/eng:epic`; confirm granularity | Creates the milestone and one ticket per section, tags `tasks.md`, commits the mapping |
| 3. Work a ticket | Run `/eng:task next` | Claims the ticket, branch, each task TDD + its own commit, reuse/interfaces, `/eng:dod`, draft PR, one review round, marks PR ready, comments the verdict |
| 4. Decide | Answer escalations; read the PR | Stops and asks on repeated findings, blocked fixes, product decisions |
| 5. Merge | You merge (squash) | Never approves or merges |
| 6. Next | `/clear`, `/eng:task next` | Picks the next ticket that is open and has no PR |

No OpenSpec in a project? Describe the change, Claude writes a `plan-change` plan, then `/eng:dod` and
`/eng:review` on the PR. Title it `[NO-ISSUE] …`, or create the issue by hand and use its tag (`[BUG-n]`, `[FEATURE-n]`, or `[ISSUE-n]` if untyped).

---

## Ticket tracking

**Structure on GitHub (default: milestone — works on free personal accounts)**
```
Milestone "Add refunds (add-refunds)"   ← one per OpenSpec change: progress bar, optional due date
 ├─ #43 1.1 Add refunds table migration       labels: task, change:add-refunds
 ├─ #44 2.1 POST /refunds endpoint            labels: task, change:add-refunds
 └─ #45 2.2 Reject refunds above order total  labels: task, change:add-refunds
```
Filter everything for a change with `label:change:add-refunds` or open the milestone page. Tasks already `[x]` get
no ticket. With `--group-by section`, each `## N.` section of `tasks.md` becomes one ticket.

| `--tracking` | What you get | Notes |
|---|---|---|
| `milestone` (default) | Milestone + `change:<name>` label | Free accounts, native progress bar |
| `epic` | Parent issue labelled `epic`, tickets as sub-issues | GitHub's *Epic* issue type is organization-only; this is a normal issue in that role |
| `both` | Milestone and parent issue | |

**The ticket tag: `[<KIND>-<n>]`.** The kind comes from the issue itself:

| Source (first match wins) | Tag |
|---|---|
| Native issue type (organization repos only — GitHub has no issue types on personal accounts) | `Bug` → `[BUG-10]`, `Feature` → `[FEATURE-10]`, `Task` → `[TASK-10]`, any custom type e.g. `Spike` → `[SPIKE-10]` |
| Type label (personal and org repos) | `bug` → BUG · `feature`/`enhancement` → FEATURE · `story` → STORY · `spike` → SPIKE · `chore` → CHORE · `task` → TASK |
| Neither | `[ISSUE-10]` (default) |

Tickets created by `/eng:epic` carry the `task` label, so they are `[TASK-n]`. Label a hand-made issue `bug` and its
PR becomes `[BUG-n] …`. Old `[ISSUE-n]` tags stay valid everywhere.

**The tag goes at the start of:**
| Where | Example |
|---|---|
| `tasks.md` (written by `/eng:epic`) | `- [ ] 2.1 [TASK-44] POST /refunds endpoint` |
| Branch name | `task-44-post-refunds-endpoint` · `bug-10-null-total` |
| Every commit | `[TASK-44] feat(refunds): add POST /refunds` · `[BUG-10] fix(refunds): handle null total` |
| PR title | `[TASK-44] feat: POST /refunds endpoint` |
| PR body | `Closes #44` (links the PR under the issue's *Development* and closes it on merge) |
| Squash-merge commit on `main` | = PR title, so `git log --grep "\-44\]"` finds everything for #44 |

**Every PR carries its own checklist**
```markdown
Closes #44
Part of milestone: Add refunds (add-refunds)

## Acceptance criteria                         ← from the OpenSpec scenarios this task implements
- [x] POST /refunds creates a refund — `RefundApiTest#creates refund`
- [ ] Refund above order total → 422          ← unchecked: not proven by a test yet

## Definition of Done                          ← fixed list from the PR template, checked from /eng:dod results
- [x] Tests written first (TDD) and passing
- [x] Build, lint and type checks pass
…
## Pending decisions                           ← anything a person must decide; "None" when empty
- [ ] Allow partial refunds? (PO)
```
- `/eng:task` writes this body, checks items **only with evidence** (a passing test or a real DoD result), and keeps
  the PR as **draft** while anything is unchecked — then tells you exactly what's open and who decides.
- The review treats a checked criterion without a test as a 🔴 BLOCKER, and an unchecked one as open work.
- Manual PRs get the same structure from `.github/pull_request_template.md`.

**What enforces it (CI, installed by `/eng:setup`)**
| Check | Fails when |
|---|---|
| `PR title` (`eng-pr-title.yml`) | Title doesn't start with `[<KIND>-<n>] ` (e.g. `[BUG-10] `) or `[NO-ISSUE] ` |
| `PR checklist` (`eng-pr-checklist.yml`) | A **ready** PR has no `Closes #n`, lacks the Acceptance criteria / DoD sections, or has any unchecked item in them or in Pending decisions. Draft PRs only get the list of pending items |

Make both required checks in branch protection. Dependabot/Renovate are exempt. `[NO-ISSUE]` PRs need no issue link
or acceptance criteria, only the DoD. `/eng:epic` also offers *squash merge, commit title = PR title* (merge commits
keep the tag) and adds autolinks for `ISSUE-`, `TASK-`, `BUG-`, `FEATURE-`, `STORY-`, `CHORE-`, `SPIKE-` so tags are
clickable (both need repo admin). The PR checklist also fails if the title tag's number differs from `Closes #n`. `openspec/changes/<change>/github.json` stores the
mapping; re-running `/eng:epic` only creates tickets for new tasks.

---

## Working as a team

Two or more devs work the same OpenSpec change in parallel without stepping on each other:

| Concern | How it's handled |
|---|---|
| **Planning dependencies** (spec time) | `/eng:spec` reviews dependencies: for each task, what must be *merged* first (tables, endpoints, types it uses). They go in `tasks.md` as `(after: 1.1)`. The lint's **Plan** shows dependency levels, the critical path and max parallel work, and warns when the tasks form a single chain only one dev can work on |
| **Dependencies on GitHub** | `/eng:epic` turns `after:` into native **blocked by** links (plus a `Depends on #n` line as fallback) — GitHub shows the ticket as blocked |
| **Dependencies found later** | `/eng:task` records them with `github_sync.py block --issue 45 --by 44` — on GitHub only, no `tasks.md` edit |
| **Who takes what** | `/eng:task` **claims** the ticket (assigns you) before branching. `next` resumes your own claims first, skips tickets assigned to others, tickets with an open PR, and blocked ones |
| **Seeing the whole picture** | `/eng:status`: ✅ done · 👀 in review (author, PR) · 🔨 in progress · ⛔ blocked (waits for #n) · 🟢 ready, plus a hint when a review would unblock someone |
| **Blocked by a teammate** | Take another ready ticket, or `--stack` on their branch; when their PR merges and the branch is deleted, GitHub retargets your PR to `main` |
| **No `tasks.md` conflicts** | Task PRs never edit `tasks.md`. A closed ticket (merged PR) is done; `/eng:epic` / `/eng:status` tick closed tasks in one `[NO-ISSUE] chore` commit |

```
Dev A: /eng:status → /eng:task next      claims #43 (lane 1)
Dev B: /eng:status → /eng:task next      #43 is claimed → claims #46 (lane 2)
B needs #43 merged first → stack on A's branch, or take #47
A merges #43 → B's stacked PR retargets to main; #44 becomes ready for whoever is free
```
Outside the plugin: branch protection with **1 required approval** (each dev reviews the other's PR after the AI review
cycle) and the `PR title`, `PR checklist` and `API contracts` checks as required.

---

## Getting it right the first time

Reviews stay strict; the writing side applies the same standard *before* the PR, so review rounds (4+ reviewers
each) come back mostly clean — fewer rounds is where the tokens are saved.

| Step | When | What it does |
|---|---|---|
| **Task plan** | `/eng:task`, before the first test | 10–15 lines: files, existing code to reuse, reference pattern, ports, tests in TDD order incl. edge/failure cases, NFR targets, open questions. Design-level MAJORs are avoided here |
| **Reference patterns** | CLAUDE.md *Patterns* (filled by `/eng:bootstrap`) | Canonical files in your repo to copy: paginated repository, validated controller, adapter with timeout, good test |
| **Static analysis** | `/eng:bootstrap` sets it up; every build runs it | detekt/ktlint, ESLint strict, ruff, semgrep packs — mechanical minors fail the build during TDD instead of costing a review round |
| **Self-check** | `self-check` skill, run by `/eng:dod` before the PR | Gates, then the author walks the diff with `checklists/self-check.md` — the **same checklist the reviewers use** (a test keeps them in sync). Same session, no extra agents |
| **Measure** | `/eng:retro` | Average rounds per PR, clean first rounds, first-round findings per 100 changed lines; recurring lintable findings become lint/semgrep rules |

---

## Spec-driven extras (on top of OpenSpec)

OpenSpec stays the planning tool (lightweight, no phase gates). These fill its gaps with scripts and CI checks —
AI tokens are only spent at the existing checkpoints.

| Gap in OpenSpec | What closes it | How |
|---|---|---|
| No check that a spec is ready to build | **Spec lint** — `/eng:spec` (`spec_lint.py`) | ERROR: requirement without scenarios, scenario without WHEN/THEN, no specs/tasks, task dependency cycles. WARN: vague wording ("fast", "properly", "etc."), no error/edge-case scenario, requirement no task covers, missing *Non-functional requirements*, L-sized tasks. Plus up to 10 ambiguity questions. `/eng:epic` refuses to create tickets while there are ERRORs |
| Specs describe behaviour, not wire contracts | **API contract check** — CI `API contracts` (`eng_contract_check.py`) | `.proto` via `buf breaking` (needs `buf.yaml`), OpenAPI via `oasdiff breaking`, both from Docker images; GraphQL/Avro flagged for review. Breaking change fails unless the PR body says `Breaking-change: approved — <reason>`. The review packet lists *Contract changes* |
| Scenarios are mostly functional | **Non-functional requirements** | OpenSpec rule: design.md gets *Non-functional requirements* (latency, volume, availability, security, observability, cost — relevant rows only). Lint warns when missing; performance/security reviewers verify against it |
| Scenarios aren't linked to tests | **Traceability** (`trace.py`) | Scenario ID `<capability>/<scenario-slug>`; tests carry `// spec: billing/refund-above-total-is-rejected`. `trace.py --list` gives IDs; reviews report untested scenarios; `/eng:spec --before-archive` blocks archiving until every scenario has a test |
| `design.md` is archived with the change | **Decision records** (`decision` skill, `decisions.py`) | `docs/decisions/NNNN-title.md`: context, options, decision, consequences; supersede chains; linked from design.md |
| No learning across changes | **Retro** — `/eng:retro` (`findings_report.py`) | Groups findings from all review ledgers by problem class; proposes one-line rules for recurring ones into `.claude/rules/learned.md` (you approve each) |
| Every change needs a proposal | **Lite path** in `/eng:task` | Tickets outside an OpenSpec change: criteria from the issue, bug → failing test first; if the fix *changes* specified behaviour it stops and asks for a change/spec update |
| `tasks.md` is a flat list | **Dependencies and size** | `- [ ] 1.2 POST /refunds (after: 1.1; size: S)` → "Depends on #n" in the ticket, `size:S` label; `/eng:task next` waits for dependencies and shows what is blocked |

**OpenSpec rules.** `/eng:bootstrap` (and `/eng:setup` on updates) merges `[eng]` rules into `openspec/config.yaml`
so OpenSpec itself writes measurable scenarios, NFR and Contracts sections, and annotated PR-sized tasks. Your own
rules are kept; only `[eng]` lines are replaced.

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

### `/eng:spec`
```text
/eng:spec                       # after /opsx:propose: lint + ≤10 ambiguity questions, then scenario IDs for tests
/eng:spec add-refunds           # a specific change
/eng:spec --before-archive      # all tasks done, all tickets closed, every scenario tested, lint clean
```
Shows ERRORs, WARNs and questions, then asks **fix all · choose · leave as is** — artifacts are only edited after you answer.

### `/eng:retro`
```text
/eng:retro            # recurring = ≥ 3 findings in ≥ 2 ledgers
/eng:retro --min 2
```
Proposes one rule line per recurring problem class; approved lines go to `.claude/rules/learned.md` (never overwritten by `/eng:setup`).

### `/eng:epic`
OpenSpec change → GitHub epic + tickets.
```text
/eng:epic                          # the active change (asks if there are several)
/eng:epic add-refunds              # a specific change
/eng:epic add-refunds --group-by task      # one ticket per task instead of per "## N." section (more PRs, more reviews)
/eng:epic add-refunds --tracking both      # milestone + parent issue with sub-issues
/eng:epic --dry-run                # show what would be created
```
1. Checks `gh` auth, validates the change (`openspec validate`), confirms `tasks.md` is approved.
2. Suggests `--group-by section` when tasks are tiny or numerous (fewer tickets → fewer PRs).
3. Previews, then creates the milestone (and/or parent issue with sub-issues), tickets, labels (`task`, `change:<name>`)
   and the tag autolinks.
4. Writes `[TASK-n]` into `tasks.md` and `github.json`; commits them (or leaves them for the first task PR if `main` is protected).
5. Offers the squash-merge repo setting. Idempotent: re-run after changing `tasks.md`.

### `/eng:task`
One ticket (a `## N.` section) → one PR, with DoD and one review round every time; tasks are its commits.
```text
/eng:task next                     # next ticket: my own claim first, else unclaimed, open, no PR, not blocked
/eng:task 44                       # a specific ticket
/eng:task 44 --depth thorough      # force a deeper review (auth, payments, migrations…)
/eng:task 45 --stack               # build on an unmerged earlier ticket's branch
```
1. Clean working tree; one task per context (asks you to `/clear` otherwise).
2. Reads the ticket and only the OpenSpec parts it needs.
3. **Claims** the ticket (assigns you; stops if a teammate has it). Looks up the tag (`[BUG-10]`, `[TASK-44]` …).
   Branch `<kind>-<n>-<slug>` from the latest default branch; if blocked, offers another ready ticket or `--stack`.
4. Works the section's tasks in order — each one TDD + its own commit `[TASK-44] feat(x): <task> (1.2)` — reuse-first, interfaces. Never edits `tasks.md` (sync ticks closed tickets). A dependency
   found mid-work is recorded with `block`. Out-of-scope discoveries become proposed new tasks, not extra code.
5. `/eng:dod` — must pass.
6. Tagged commits, push, **draft** PR titled `[<KIND>-n] <type>: <task>` with `Closes #n`, the milestone and
   labels, and checklists for acceptance criteria, DoD and pending decisions (see [Ticket tracking](#ticket-tracking)).
7. **One review round** on the PR — every dedicated reviewer, then it stops for your decision, fixes what you chose
   and confirms with build/tests/lint + self-check (no second AI round).
8. Everything checked with evidence → PR marked ready + one verdict comment. Anything open (pending decision,
   unproven criterion, escalation) → stays draft with the open items listed. Never merges.

### `/eng:dod`
Run before saying a task is finished or opening a PR (`/eng:task` runs it for you).
Checks: build, tests, lint (real output) · diff only touches the task · no debug code/TODOs · reuse applied ·
interfaces for external deps · TDD followed · every requirement implemented · docs/.env.example updated ·
`secure-self-review` passed. Ends with a `Done / Changed / Verified / Security / Follow-ups` summary; failures go at the top.

### `/eng:review`
One review round per PR by default (`/eng:task` runs it for you): review → checkpoint → fix → gates + self-check.
```text
/eng:review                       # current branch vs main
/eng:review 42                    # PR #42
/eng:review 42 --depth thorough   # depth of round 1 (default: triage decides)
/eng:review 42 --max-rounds 3     # default 1 — >1 re-reviews fixes with fresh reviewers
/eng:review 42 --auto             # no checkpoints — only for unattended runs
```
After the round it stops: shows the full findings table and the Coverage section, then asks
**Fix required** (BLK, MAJ, answer Q) · **Fix required + minors** · **Choose** IDs (decline others with a reason) ·
**Stop here**. Nothing is edited until you answer.
See [Review cycle in detail](#review-cycle-in-detail).

### `/eng:review-once`
**One** read-only review round — reports findings, fixes nothing. For someone else's PR or a quick opinion.
```text
/eng:review-once 42                    # PR #42
/eng:review-once 42 --depth thorough   # standard (default) | thorough | quick (only when you ask)
```
1. Builds a **review packet** once (`scripts/review_packet.py`): diff, changed files, requirement sources, triage.
2. Deterministic gates first: build, tests, lint, gitleaks, semgrep (if installed).
3. Launches only the reviewers the change needs, in parallel, each reading the packet:

   | Depth | Reviewers | When |
   |---|---|---|
   | `standard` (default) | `requirements-verifier` + `performance-reviewer` + `security-reviewer` + `code-reviewer` + installed `pr-review-toolkit` agents (sonnet) | Every PR |
   | `thorough` | the same reviewers on **opus** | Auth, payments, migrations, public APIs |
   | `quick` | `code-reviewer` alone (covers requirements, security, efficiency itself) | **Only when you explicitly ask** |

   Triage never removes a reviewer; it only adds *focus hints* (e.g. "security focus: yes"). Every check is covered
   at every depth (`tests/test_review_coverage.py` enforces it). Set a project minimum in CLAUDE.md:
   `Minimum review depth: standard` (default) or `thorough`.
4. Confirms every 🔴/🟠 finding against the code; drops false positives.
5. Report (tables): **coverage** (depth and why, reviewers run/skipped, files reviewed, what was not checked),
   gates, requirements traceability, every finding with ID and proposed fix, verdict. Asks before fixing anything.
   Say "post it to the PR" to comment via `gh`.

### Planning commands (OpenSpec)
| Command | When |
|---|---|
| `/opsx:propose`, `/opsx:apply`, `/opsx:archive` | Projects with OpenSpec (`openspec init --tools claude`). Use `/eng:task` instead of `/opsx:apply` to get one PR per section |
| "plan this change" → `plan-change` skill | Projects without OpenSpec; plan in chat or `docs/plans/<date>-<slug>.md` |

---

## Skills Claude uses automatically

You don't need to call these; the rules and skill descriptions make Claude use them at the right moment.
You can still ask for them by name ("use the tdd skill"). Choosing the least code (reuse → stdlib → dependency → one
line) is ponytail's job — see [Companion plugins](#companion-plugins-ponytail-and-pstack).

| Skill | Triggers when | What it enforces |
|---|---|---|
| `tdd` | Implementing any feature, change or bug fix | One failing test (shown failing) → minimum code (shown passing) → refactor. Code written before its test is deleted |
| `interface-first-design` | Adding anything external or replaceable (DB, cache, queue, API, storage, payments, clock…) | Port in the domain, adapter in infrastructure, DI wiring, fake + integration + contract tests |
| `plan-change` | Change bigger than one file, no `openspec/` folder | Goal, out of scope, approach, TDD-ordered steps, risks — then waits for approval |
| `secure-self-review` | Code touching input, auth, data, config, secrets, network, deps; always in done/review | gitleaks / semgrep / dependency audit if installed + manual checklist; HIGH/CRITICAL fixed before done |

---

## Companion plugins: ponytail and pstack

eng is the process (specs → tickets → TDD → DoD → review → PR). Two plugins cover the rest, and eng no longer
duplicates them:

| Plugin | What it brings | Replaced in eng |
|---|---|---|
| [ponytail](https://github.com/DietrichGebert/ponytail) | Always on (hook): need it? → already in the codebase? → stdlib → installed dependency → one line → minimum code. Comments say why, not how. `/ponytail lite\|full\|ultra\|off`, `/ponytail-review` (delete list for a diff), `/ponytail-audit` | `reuse-first` skill; the "search first / no premature abstraction / why-not-how" rule lines |
| [pstack](https://github.com/cursor/plugins/tree/main/pstack) | Manual skills: `/pstack:poteto-mode` (reproduce → root cause → smallest fix → re-run), `/pstack:how`, `/pstack:why`, `/pstack:teach`, `/pstack:unslop`, `/pstack:architect` … | nothing — eng had no equivalent |

Where they disagree, the eng rules win (`.claude/rules/workflow.md`): TDD for every behaviour (pstack's `tdd` is
"only when asked", ponytail tests only non-trivial logic); ports for external dependencies are required structure, not
speculative abstraction — so read `/ponytail-audit` "single-implementation interface" findings with that in mind;
public APIs keep their doc comments (pstack's `no-comments` would strip them). Reviews stay `/eng:review`;
pstack's `interrogate`, `arena` and `swarm` spawn many agents — use them only for decisions that deserve it.

---

## Reviewer agents

Read-only subagents with their own context, so they don't grade their own work. Used by `review-once` / `review`,
or directly: *"use the requirements-verifier agent on this branch"*. All read the shared review packet first and
answer with tables only.

| Agent | Default model | Role |
|---|---|---|
| `requirements-verifier` | sonnet (opus in thorough) | Requirement → code → test traceability — every round |
| `security-reviewer` | sonnet (opus in thorough) | Secrets, backdoors, injection, authz, data exposure, crypto, supply chain, infra |
| `performance-reviewer` | sonnet (opus in thorough) | Efficiency at expected scale — every standard/thorough review |
| `code-reviewer` | sonnet (opus in thorough) | Tests, correctness, architecture, design, readability (+ requirements/security/efficiency in quick mode) |
| `fix-verifier` | haiku | Re-review rounds: verifies fixes against the remediation diff, flags regressions |

### `requirements-verifier`
- Collects requirements from the OpenSpec change (proposal, tasks, every scenario), `docs/plans/`, PR body, linked issues.
- Builds a table **requirement → code (file:line) → test** with status ✅ Done · ⚠️ Partial · ❌ Missing · 🐞 Wrong · 🧪 Untested.
- Lists unchecked tasks and **scope creep** (changed code that maps to no requirement).
- Checks each requirement has a test that would fail without the code.

### `security-reviewer`
- Dedicated security pass: secrets and PII exposure, backdoors, disabled controls (TLS, CSRF, CORS), injection,
  path traversal, XSS, SSRF, deserialization, authn/authz (IDOR, tokens), crypto and password hashing,
  dependencies and outbound calls, IAM/Docker/CI/Terraform in the diff. Confirms or dismisses gitleaks/semgrep hits.

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

**Default (since 3.0): one round per PR.** Round 1 → checkpoint → remediation → gates (build, tests, lint) +
self-check on the fixes → items marked `FIXED (self-verified)` → done. 🔴/🟠 you chose not to fix stay OPEN and are
listed under the PR's *Pending decisions*. The loop below only runs with `--max-rounds N` > 1.

```
Round 1  FULL review ──► findings ──► ledger
   ▼
Checkpoint  full findings table + coverage → YOU choose: fix required · + minors · pick IDs · stop
   ▼
Remediation  only the chosen IDs: fixes with TDD, answers questions
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
| VERIFY | `requirements-verifier` + `fix-verifier` (haiku) | Remediation diff + ledger |

### Roles
- **Reviewers** — fresh subagents each round; raise findings, verify previous fixes (VERIFIED / REOPENED), never edit code.
- **Author** — your session; fixes in order 🔴 → 🟠 → ❓ → 🟡 → 💡, bugs via a failing test first, commits as
  `[TASK-44] fix(review): R1-MAJ-3 …`. It cannot verify its own fixes.

### Fixing a blocker or major: the fix brief
Patching the line a reviewer pointed at is how the same major comes back next round. Before editing, each chosen
🔴/🟠 gets a short brief in the ledger: the failing scenario, the root cause (where the rule *should* be enforced),
every other place with the same problem class, the one fix site, and two tests — the reviewer's scenario and a
variant — shown failing first. A finding seen twice also says why the last fix missed. `fix_brief_check.py <ledger>`
must pass before anything is marked FIXED:

```markdown
#### R1-MAJ-2
- Fails when: refund amount 0 via the queue → 201 Created; expected 422
- Root cause: amount validated in the controller only; the consumer path bypasses it
- Same class elsewhere: RefundConsumer.kt:40, PartialRefundHandler.kt:22
- Fix site: Money value object rejects non-positive amounts in its constructor
- Tests: `rejects zero refund` (failed first: yes), `consumer rejects zero refund` (failed first: yes)
```

### Exit criteria — single round (default)
- Build, full tests, lint and the self-check green on the final commit.
- Every chosen finding `FIXED (self-verified)` with its commit; 🔴/🟠 left open are listed in the PR's Pending decisions
  (the PR stays draft while any is undecided).

### Exit criteria — multi-round (`--max-rounds N`)
- Build, full tests, lint green on the final commit.
- Latest requirements check: every requirement ✅ Done (no Missing / Partial / Wrong / Untested), no fix escalated since.
- No open or reopened 🔴, 🟠 or ❓; every 🟡 verified or declined with a reason.
- Every fix from the last remediation verified by a reviewer.

### When it stops and asks you
- Max rounds reached (default 1).
- A finding's fingerprint (component · problem class) seen a 3rd time — variants of the same problem count.
  On the 2nd time the author must fix the root cause across all variants, not just the reported example.
- A hook, permission or tool error blocks the same fix twice (Claude never rewords content to get past a guard).
- Author disagrees with a 🔴/🟠 finding.
- A question needs a product/business decision.

### The ledger
`openspec/changes/<change>/reviews/<branch>/ledger.md` (OpenSpec) or `.reviews/<branch>/ledger.md`. One table per round with
stable IDs, a fingerprint and `Seen` count per finding, and statuses
`OPEN → FIXED (self-verified) · FIXED → VERIFIED / REOPENED · DECLINED · ANSWERED · SUPERSEDED → <ID>`.

### Finding IDs
`R<round>-<code>-<n>` — round raised, type/severity code, running number (unique per ledger):

| Code | Meaning | Example |
|---|---|---|
| `BLK` | 🔴 Blocker | `R1-BLK-3` |
| `MAJ` | 🟠 Major | `R1-MAJ-7` |
| `MIN` | 🟡 Minor | `R2-MIN-12` |
| `S` | 💡 Suggestion | `R1-S-9` |
| `Q` | ❓ Question | `R1-Q-4` |

IDs never change; if a finding's severity or type changes (a question reveals a bug), the old ID is marked
`SUPERSEDED → R2-MAJ-15` and the new one carries the history. Commits reference the ID after the ticket tag. Commit it as the PR's
audit trail, or add `.reviews/` to `.gitignore`.

### Final report
```
Review complete — 1 round — verdict: READY FOR HUMAN REVIEW
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

Shell commands: only arguments of programs that read file contents (`cat`, `less`, `cp`, `base64`, `source`, the
file arguments of `grep`/`rg`, `< file` redirects…) are treated as file reads. Words like `key`, `credentials` or
`secrets` in a `grep` pattern, commit message or `kubectl get secrets` are not blocked; `cat ~/.aws/credentials` is.
Source code inside a folder named `secrets/` (e.g. a `SecretService.kt` package) is readable; data files there are not.

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
| All reviewers, focused | Every reviewer runs (no skipping); triage only gives focus hints |
| Cheaper models | Reviewers on sonnet, fix verification on haiku; opus only with `--depth thorough` |
| Read once | One review packet per round instead of each reviewer exploring the repo |
| Tools before AI | Build/tests/lint/gitleaks/semgrep run first; reviewers don't repeat them |
| Smaller re-reviews | Later rounds read only the remediation diff; max 3 rounds |
| Small always-on cost | Review skills are manual-only; all descriptions are short |

Your habits matter as much:
- **`/clear` between tasks** — a long session re-sends its whole history on every request. Start each review in a fresh session.
- **Disable skills/plugins you don't use** in `/plugin` — every enabled skill's description is sent on every request.
- **Pick the depth on purpose:** `thorough` (opus) for risky changes; `quick` only if you explicitly accept a single reviewer.
- Check what a review cost with `/cost` (or the usage view) and compare depths.

---

## Developing this repo

See `CLAUDE.md`. Quick check:
```bash
python3 scripts/validate.py && shellcheck install.sh plugins/eng/install.sh && pytest -q
claude --plugin-dir ./plugins/eng   # try plugin changes locally
```
