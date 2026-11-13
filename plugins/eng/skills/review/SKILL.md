---
name: review
description: One review round per PR (all reviewers), checkpoint, fix the chosen findings, confirm with gates + self-check. More rounds only on request.
disable-model-invocation: true
argument-hint: "[PR# | base branch] [--depth standard|thorough|quick] [--max-rounds N (default 1)] [--auto]"
---

# Review cycle

Two roles, never mixed:
- **Reviewers** = fresh subagents launched each round by following `${CLAUDE_PLUGIN_ROOT}/skills/review-once/SKILL.md`
  (read that file; do not re-explain it). They raise findings; they never edit code.
- **Author** = this session. It remediates findings; it never marks its own fix as verified — the next round does.

## Severity and finding types

| Severity | Code | Meaning | Must be resolved to exit? |
|----------|------|---------|---------------------------|
| 🔴 BLOCKER | `BLK` | Broken build/tests, missing or wrong requirement, **missing tests for a requirement**, TDD not followed, security vulnerability, leaked secret, data loss risk | Yes — fixed |
| 🟠 MAJOR | `MAJ` | Bug in an edge case, serious performance problem at expected scale, broken architecture rule (concrete dependency in domain, duplicated logic), silent failure | Yes — fixed |
| 🟡 MINOR | `MIN` | Naming, comments, small inefficiency, missing edge-case test for non-critical path | Yes — fixed OR declined with a written reason |
| 💡 SUGGESTION | `S` | Optional improvement / alternative approach | No — accept or decline with reason |
| ❓ QUESTION | `Q` | Reviewer needs clarification; may hide a bug | Yes — answered (and converted to a finding if the answer reveals a problem) |

### Finding IDs: `R<round>-<code>-<n>`
- `R1-BLK-3`, `R1-MAJ-7`, `R2-MIN-12`, `R1-Q-4`, `R1-S-9` — round raised · code from the table · number.
- `<n>` is one running counter per ledger across all codes, so the number alone is unique (`R1-BLK-3` and `R1-Q-3`
  never both exist).
- IDs never change. If a finding's severity or type changes (a question reveals a bug, a MINOR turns out MAJOR),
  mark the old row `SUPERSEDED → <new ID>` and raise a new ID with the new code, e.g. `R1-Q-4` → `R2-MAJ-15`.
  Its fingerprint and `Seen` count carry over.
- Use the full ID everywhere: ledger, reports, PR comments, commit messages.

**Recurrence tracking (prevents loops).** Each finding has a *fingerprint*: `<file or component> · <problem class>`
(e.g. `DatabaseConfig · credential leak in JDBC URL`). Before adding a finding, match it against EVERY ledger row,
whatever its status, by fingerprint — not by exact wording or line number. A match reuses the existing ID, is marked
REOPENED, and increments its `Seen` count. A variant of the same problem (another URL format, another endpoint)
is the same fingerprint, not a new finding.

## The ledger (single source of truth)
Location: `openspec/changes/<change>/reviews/<branch-name>/ledger.md` if an OpenSpec change is active, otherwise
`.reviews/<branch-name>/ledger.md` (one ledger per branch/PR, so per-task PRs never share one). Create it in round 1; append every round; never delete history.

```markdown
# Review ledger — <change / PR> (base: <base>)

## Round 1 — <date> — scope: FULL — changed lines: <from the packet> — verdict: REQUEST CHANGES
| ID | Fingerprint | Area | Location | Finding | Seen | Status | Resolution |
|----|-------------|------|----------|---------|------|--------|------------|
| R1-BLK-1 | RefundService · missing test for requirement | requirements | — | R3 "refund over limit returns 422" has no test | 1 | VERIFIED | test `rejects refund above limit` + fix (abc123) |
| R1-MIN-2 | Foo · unclear name | quality | Foo.kt:42 | rename `proc` | 1 | DECLINED | public API, rename in separate change |
| R1-Q-3 | RefundRepository · unbounded query | perf | Repo.kt:88 | expected row count per tenant? | 1 | SUPERSEDED → R2-MAJ-4 | answer: unbounded — needs pagination |

## Round 2 — <date> — scope: TARGETED — verdict: APPROVE
| R2-MAJ-4 | RefundRepository · unbounded query | perf | Repo.kt:88 | findAll loads every refund | 1 | VERIFIED | paginated, test `pages refunds` (def456) |

Statuses: OPEN → FIXED (self-verified) [single round] · FIXED (author) → VERIFIED / REOPENED (next round) · DECLINED · ANSWERED · DEFERRED → #<issue> · SUPERSEDED → <ID>
```

## Default: one review round per PR (`--max-rounds 1`)
Review once with every reviewer (round 1, scope FULL) → checkpoint → fix the chosen findings → confirm the fixes with
the deterministic gates and the `self-check` skill — **no second AI review round**. The author marks each fixed item
`FIXED (self-verified)` with the commit ref; the PR's human reviewer gives the final approval.
Re-review rounds (the loop below) run only when the user passes `--max-rounds N` with N > 1.

## Loop (rounds 2+ only with `--max-rounds N` > 1)

### Round N — Review
1. Run one review-once round with the scope chosen below and the ledger path. Round 1 uses `--depth` (or the packet's
   suggestion) at scope FULL; later rounds build the packet with `--since <last reviewed commit>` so reviewers
   read only the remediation diff.
2. Reviewers must: (a) verify every FIXED item → VERIFIED or REOPENED (with reason), (b) check for regressions
   introduced by the fixes, (c) raise new findings with severity, (d) NOT re-raise DECLINED/ANSWERED items
   unless the code changed in a way that makes them relevant again.
3. Append the round's table to the ledger, under a header `## Round <N> — <date> — scope: <S> — changed lines: <from the packet> — verdict: <V>`
   (`/eng:retro` uses it to measure first-round quality). If exit criteria are met → go to **Exit**.

### Round N — Checkpoint (mandatory unless the user passed `--auto`)
**Never start remediation on your own.** After every review round:
1. Show the user the round report in full — every finding as a row with its ID, area, location, the problem in one
   line and the proposed fix — plus the **Coverage** section. Never summarise as "found some issues".
2. Ask one question (use the AskUserQuestion tool when available; otherwise ask in text) and **end your turn**:
   - **Fix required, ticket the minors** (recommended) — every BLK and MAJ, answer every Q; MIN and S go to ONE
     follow-up issue (`gh issue create` listing their IDs and rows, linked from the PR) and become `DEFERRED → #<n>`
   - **Fix required + minors** — also every MIN; S only if trivial (minor-fix rule below)
   - **Choose** — the user lists IDs to fix, and may decline others with a reason
   - **Stop here** — leave the ledger as is; report what is still open
3. Do not edit any file until the user answers. Record the decision in the ledger under the round
   (`Decision: fix R1-BLK-1, R1-MAJ-2; declined R1-MIN-3 (user: out of scope)`). User-declined items are
   `DECLINED (user)`; a declined BLK/MAJ means exit criteria cannot be met — say so, and end as `STOPPED BY USER`.
4. No user available (scheduled/unattended run) and no `--auto` → stop after the report; never fix unasked.
`--auto` (only when the user asked for it) skips this checkpoint, fixing BLK, MAJ, Q and MIN; stop conditions still apply.

### Round N — Remediation (author) — only the IDs the user chose
Work through the chosen findings in order BLOCKER → MAJOR → QUESTION → MINOR → SUGGESTION.

**Every BLOCKER/MAJOR gets a fix brief before any edit** — the flagged line is where the problem showed, rarely where
it lives. Write it in the ledger under `## Fix briefs` → `#### <ID>`:
```markdown
#### R1-MAJ-2
- Fails when: <input/state> → <wrong outcome>; expected <correct outcome>   (the reviewer's scenario, made concrete)
- Root cause: <why the code allowed it — ask "why" until you reach where the rule SHOULD be enforced>
- Same class elsewhere: <every other place in the change/module with this problem class, or "none — searched <how>">
- Fix site: <the ONE place that enforces it for all callers: shared validator, type/constructor, port, query builder>
- Tests: `<reviewer's scenario>` (failed first: yes), `<a variant: other input/endpoint/path>` (failed first: yes)
- Previous fix missed: <only when Seen ≥ 2 — why the last fix didn't hold>
```
Then: write both tests and show them failing → fix at the fix site (and every place in *Same class elsewhere*) →
show them passing → re-read the finding and confirm each claim in it is addressed. A finding you cannot reproduce
with a failing test is not understood yet — ask the user or the reviewer's text, never guess-fix.
Before marking any BLK/MAJ FIXED run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fix_brief_check.py" <ledger>`; it must exit 0.

- **Bugs / missing behaviour / missing tests:** TDD — write a failing test that reproduces the finding, show it fail,
  fix, show it pass (`tdd` skill). Never weaken an existing test to resolve a finding.
- **Questions:** answer from code/spec. If the answer needs a product or business decision, ask the user and pause the loop.
  If the answer reveals a problem, convert it into a new finding with a severity.
- **Minor / suggestions:** fix, or DECLINE with a concrete reason (scope, trade-off, conflicts with spec). No silent ignores.
  **Minor-fix rule:** a MIN/S fix only changes existing code (about 20 lines at most) — no new module, config option,
  logging channel, workflow or dependency. Bigger → `DEFERRED → #<follow-up issue>`. New code added by fixes is where
  later rounds find new problems.
- **Disagreement on a BLOCKER/MAJOR:** do not decline it yourself — write your reasoning in the ledger and ask the user to decide.
- Commit per finding or per logical group, ticket tag first: `[TASK-44] fix(review): R1-BLK-1 add refund limit test and validation`.
- Run the gates (build, tests, lint) after remediation. Mark items FIXED with commit refs.

### Choose the next round's scope
| Highest severity fixed this round | Next round | Reviewers (cost) |
|-----------------------------------|------------|------------------|
| Any 🔴 BLOCKER, or fixes touched > ~30% of the diff, or new files/ports added | **FULL** | same set as round 1 |
| 🟠 MAJOR | **TARGETED** | `requirements-verifier` + reviewers for the affected areas, remediation diff only |
| Only 🟡 MINOR / 💡 / ❓ | **VERIFY** | `requirements-verifier` + `fix-verifier`, remediation diff only |
| Nothing changed (all declined/answered) | — | no new round |

Gates (build, tests, lint) run in EVERY round — failing or missing tests are always a 🔴 BLOCKER.
If `fix-verifier` returns `ESCALATE: TARGETED`, run a TARGETED round instead of exiting.

**Token hygiene:** the ledger + packet carry all state between rounds. Do not paste earlier rounds' reports back
into the conversation; reference the ledger. If the session is long before starting, suggest `/clear` first.

## Exit criteria — single round (default)
- [ ] Build, full test suite, lint and the `self-check` pass after remediation.
- [ ] `fix_brief_check.py <ledger>` exits 0 (every fixed BLK/MAJ has its brief and a test that failed first).
- [ ] Every finding the user chose is `FIXED (self-verified)` with a commit ref; every Q is answered.
- [ ] BLOCKER/MAJOR findings the user chose not to fix stay `OPEN` and are listed in the PR's *Pending decisions*
      (so the PR stays draft until someone decides) — never silently dropped.
- [ ] PR body: `Closes #n`, and every *Acceptance criteria* / *Definition of Done* item checked with evidence.

## Exit criteria — multi-round (`--max-rounds N` > 1; all must hold)
- [ ] Build, full test suite and lint pass on the final commit.
- [ ] `requirements-verifier` in the final round (it runs every round; `code-reviewer`'s check only in explicit quick mode): every requirement ✅ Done — no Missing, Partial, Wrong or Untested.
- [ ] No OPEN or REOPENED BLOCKER, MAJOR or QUESTION. Every MINOR is VERIFIED or DECLINED with reason.
- [ ] Every FIXED item from the last remediation has been VERIFIED by a reviewer (the author cannot self-verify).
- [ ] When reviewing a PR: its body links the issue (`Closes #n`) and every *Acceptance criteria*, *Definition of Done*
      and *Pending decisions* item is checked with evidence. Unchecked items are reported as open, not as passed.

## Stop conditions
- Default **1 round**; with `--max-rounds N`, at most N. If reached, stop and report what is still open and why it keeps recurring.
- A fingerprint seen for the **2nd time** (reopened or re-raised) → the author fixes the *root cause* across all
  variants, not the reported example, and states which variants the fix covers.
- A fingerprint seen for the **3rd time** → STOP. Do not attempt another fix. Report to the user: the finding,
  the attempts so far, why each failed, and options. The approach needs a human decision.
- **Blocked remediation** — a hook, permission rule or tool error blocks the same fix step twice → STOP and ask.
  Never reword, split or obfuscate content to get past a guard (e.g. the secret guard); the block itself is the
  information. Record it in the ledger as `BLOCKED: <tool> — <message>`.
- Never exit by lowering severities, deleting ledger rows, or skipping reviewers.

## Exit report
```
Review complete — <N> round(s) — verdict: READY FOR HUMAN REVIEW / BLOCKED
Findings: <total> raised · <fixed> fixed (self-verified / verified) · <declined> declined · <answered> answered
Open (if blocked): <IDs + one line each>
Ledger: <path>
```
