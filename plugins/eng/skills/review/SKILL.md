---
name: review
description: Review → fix → re-review rounds until merge-ready; severity decides each next round's scope; findings tracked in a ledger.
disable-model-invocation: true
argument-hint: "[PR# | base branch] [--depth quick|standard|thorough] [--max-rounds N]"
---

# Review cycle

Two roles, never mixed:
- **Reviewers** = fresh subagents launched each round by following `${CLAUDE_PLUGIN_ROOT}/skills/review-once/SKILL.md`
  (read that file; do not re-explain it). They raise findings; they never edit code.
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

**Recurrence tracking (prevents loops).** Each finding has a *fingerprint*: `<file or component> · <problem class>`
(e.g. `DatabaseConfig · credential leak in JDBC URL`). Before adding a finding, match it against EVERY ledger row,
whatever its status, by fingerprint — not by exact wording or line number. A match reuses the existing ID, is marked
REOPENED, and increments its `Seen` count. A variant of the same problem (another URL format, another endpoint)
is the same fingerprint, not a new finding.

## The ledger (single source of truth)
Location: `openspec/changes/<change>/reviews/ledger.md` if an OpenSpec change is active, otherwise
`.reviews/<branch-name>/ledger.md`. Create it in round 1; append every round; never delete history.

```markdown
# Review ledger — <change / PR> (base: <base>)

## Round 1 — <date> — scope: FULL — verdict: REQUEST CHANGES
| ID | Sev | Type | Area | Fingerprint | Location | Finding | Seen | Status | Resolution |
|----|-----|------|------|----------|---------|--------|------------|
| R1-1 | 🔴 | issue | requirements | — | R3 "refund over limit returns 422" has no test | VERIFIED | test `rejects refund above limit` + fix (abc123) |
| R1-2 | 🟡 | suggestion | quality | Foo.kt:42 | rename `proc` | DECLINED | public API, rename in separate change |
| R1-3 | ❓ | question | perf | Repo.kt:88 | expected row count? | ANSWERED | ≤ 5k per tenant (spec §2) |

Statuses: OPEN → FIXED (author) → VERIFIED / REOPENED (next round reviewer) · DECLINED · ANSWERED
```

## Loop

### Round N — Review
1. Run one review-once round with the scope chosen below and the ledger path. Round 1 uses `--depth` (or the packet's
   suggestion) at scope FULL; later rounds build the packet with `--since <last reviewed commit>` so reviewers
   read only the remediation diff.
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
| Highest severity fixed this round | Next round | Reviewers (cost) |
|-----------------------------------|------------|------------------|
| Any 🔴 BLOCKER, or fixes touched > ~30% of the diff, or new files/ports added | **FULL** | same set as round 1 |
| 🟠 MAJOR | **TARGETED** | `requirements-verifier` + reviewers for the affected areas, remediation diff only |
| Only 🟡 MINOR / 💡 / ❓ | **VERIFY** | `fix-verifier` (haiku) only, remediation diff only |
| Nothing changed (all declined/answered) | — | no new round |

Gates (build, tests, lint) run in EVERY round — failing or missing tests are always a 🔴 BLOCKER.
If `fix-verifier` returns `ESCALATE: TARGETED`, run a TARGETED round instead of exiting.

**Token hygiene:** the ledger + packet carry all state between rounds. Do not paste earlier rounds' reports back
into the conversation; reference the ledger. If the session is long before starting, suggest `/clear` first.

## Exit criteria (all must hold)
- [ ] Build, full test suite and lint pass on the final commit.
- [ ] Latest `requirements-verifier` result (FULL/TARGETED round, or quick-mode check): every requirement ✅ Done — no Missing, Partial, Wrong or Untested, and no later fix escalated.
- [ ] No OPEN or REOPENED BLOCKER, MAJOR or QUESTION. Every MINOR is VERIFIED or DECLINED with reason.
- [ ] Every FIXED item from the last remediation has been VERIFIED by a reviewer (the author cannot self-verify).

## Stop conditions
- Default max **3 rounds** (or `--max-rounds`). If reached, stop and report what is still open and why it keeps recurring.
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
Review cycle complete — <N> rounds — verdict: READY TO MERGE / BLOCKED
Findings: <total> raised · <fixed+verified> fixed · <declined> declined · <answered> answered
Open (if blocked): <IDs + one line each>
Ledger: <path>
```
