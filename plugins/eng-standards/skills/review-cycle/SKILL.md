---
name: review-cycle
description: Iterative review → remediation → re-review loop for a change or PR. Each round reviewers raise findings (issues, suggestions, questions) with severity; the author fixes or answers them; severity decides the scope of the next review round; repeats until exit criteria are met (gates green, all requirements implemented and tested, no open blocking findings). Use when the user asks to review until done, run review rounds, or get a change merge-ready.
argument-hint: "[PR number | base branch] [--max-rounds N]"
---

# Review cycle

Two roles, never mixed:
- **Reviewers** = fresh subagents launched by the `pr-review` skill each round. They raise findings; they never edit code.
- **Author** = this session. It remediates findings; it never marks its own fix as verified — the next round does.

## Severity and finding types

| Severity | Meaning | Must be resolved to exit? |
|----------|---------|---------------------------|
| 🔴 BLOCKER | Broken build/tests, missing or wrong requirement, **missing tests for a requirement**, TDD not followed, security vulnerability, leaked secret, data loss risk | Yes — fixed |
| 🟠 MAJOR | Bug in an edge case, serious performance problem at expected scale, broken architecture rule (concrete dependency in domain, duplicated logic), silent failure | Yes — fixed |
| 🟡 MINOR | Naming, comments, small inefficiency, missing edge-case test for non-critical path | Yes — fixed OR declined with a written reason |
| 💡 SUGGESTION | Optional improvement / alternative approach | No — accept or decline with reason |
| ❓ QUESTION | Reviewer needs clarification; may hide a bug | Yes — answered (and converted to a finding if the answer reveals a problem) |

Finding IDs are stable across rounds: `R<round>-<n>` (e.g. `R1-3`). Never renumber.

## The ledger (single source of truth)
Location: `openspec/changes/<change>/reviews/ledger.md` if an OpenSpec change is active, otherwise
`.reviews/<branch-name>/ledger.md`. Create it in round 1; append every round; never delete history.

```markdown
# Review ledger — <change / PR> (base: <base>)

## Round 1 — <date> — scope: FULL — verdict: REQUEST CHANGES
| ID | Sev | Type | Area | Location | Finding | Status | Resolution |
|----|-----|------|------|----------|---------|--------|------------|
| R1-1 | 🔴 | issue | requirements | — | R3 "refund over limit returns 422" has no test | VERIFIED | test `rejects refund above limit` + fix (abc123) |
| R1-2 | 🟡 | suggestion | quality | Foo.kt:42 | rename `proc` | DECLINED | public API, rename in separate change |
| R1-3 | ❓ | question | perf | Repo.kt:88 | expected row count? | ANSWERED | ≤ 5k per tenant (spec §2) |

Statuses: OPEN → FIXED (author) → VERIFIED / REOPENED (next round reviewer) · DECLINED · ANSWERED
```

## Loop

### Round N — Review
1. Run the `pr-review` skill with the scope chosen below, passing the ledger path so reviewers can see prior findings.
2. Reviewers must: (a) verify every FIXED item → VERIFIED or REOPENED (with reason), (b) check for regressions
   introduced by the fixes, (c) raise new findings with severity, (d) NOT re-raise DECLINED/ANSWERED items
   unless the code changed in a way that makes them relevant again.
3. Append the round's table to the ledger. If exit criteria are met → go to **Exit**.

### Round N — Remediation (author)
Work through findings in order BLOCKER → MAJOR → QUESTION → MINOR → SUGGESTION:
- **Bugs / missing behaviour / missing tests:** TDD — write a failing test that reproduces the finding, show it fail,
  fix, show it pass (`tdd` skill). Never weaken an existing test to resolve a finding.
- **Questions:** answer from code/spec. If the answer needs a product or business decision, ask the user and pause the loop.
  If the answer reveals a problem, convert it into a new finding with a severity.
- **Minor / suggestions:** fix, or DECLINE with a concrete reason (scope, trade-off, conflicts with spec). No silent ignores.
- **Disagreement on a BLOCKER/MAJOR:** do not decline it yourself — write your reasoning in the ledger and ask the user to decide.
- Commit per finding or per logical group: `fix(review): R1-1 add refund limit test and validation`.
- Run the gates (build, tests, lint) after remediation. Mark items FIXED with commit refs.

### Choose the next round's scope
| Highest severity fixed this round | Next round |
|-----------------------------------|------------|
| Any 🔴 BLOCKER, or fixes touched > ~30% of the diff, or new files/ports added | **FULL** — all reviewers on the whole change |
| 🟠 MAJOR | **TARGETED** — reviewers for the affected areas (e.g. performance, requirements) on changed files + verify all FIXED items |
| Only 🟡 MINOR / 💡 / ❓ | **VERIFY** — one reviewer confirms each FIXED item and checks the remediation diff for regressions |
| Nothing changed (all declined/answered) | No new round needed |

Requirements verification and test-coverage checks run in EVERY round, whatever the scope —
missing tests are always a BLOCKER.

## Exit criteria (all must hold)
- [ ] Build, full test suite and lint pass on the final commit.
- [ ] `requirements-verifier`: every requirement ✅ Done — no Missing, Partial, Wrong or Untested.
- [ ] No OPEN or REOPENED BLOCKER, MAJOR or QUESTION. Every MINOR is VERIFIED or DECLINED with reason.
- [ ] Every FIXED item from the last remediation has been VERIFIED by a reviewer (the author cannot self-verify).

## Stop conditions
- Default max **5 rounds** (or `--max-rounds`). If reached, stop and report what is still open and why it keeps recurring.
- Same finding REOPENED twice → stop and ask the user; the approach probably needs rethinking.
- Never exit by lowering severities, deleting ledger rows, or skipping reviewers.

## Exit report
```
Review cycle complete — <N> rounds — verdict: READY TO MERGE / BLOCKED
Findings: <total> raised · <fixed+verified> fixed · <declined> declined · <answered> answered
Open (if blocked): <IDs + one line each>
Ledger: <path>
```
