---
name: pr-review
description: One review round of a pull request or branch — requirements fulfilment, correctness against the spec, TDD/test quality, efficiency, security, and code quality — run by independent reviewer subagents and consolidated into severity-ranked findings and a verdict. Use for a single review; use review-cycle to iterate review → fix → re-review until done. Accepts an optional PR number or base branch.
argument-hint: "[PR number | base branch] [--scope FULL|TARGETED|VERIFY] [--ledger path]"
---

# PR review (one round)

Reviewers must be independent of the author: run the checks in **subagents** (fresh context), never by re-reading
your own reasoning from this session. Severity scale and finding types are defined in
the `review-cycle` skill (in this plugin: `${CLAUDE_PLUGIN_ROOT}/skills/review-cycle/SKILL.md`) (🔴 BLOCKER · 🟠 MAJOR · 🟡 MINOR · 💡 SUGGESTION · ❓ QUESTION) — use them everywhere.

## 1. Scope the review
- PR number → `gh pr view <n> --json number,title,body,baseRefName,headRefName` and fetch/check out the head.
  Otherwise base = given branch or `main`; head = current branch.
- Collect: `git diff --stat <base>...HEAD`, changed files, requirement sources
  (active `openspec/changes/*`, `docs/plans/*`, PR body, linked issues).
- `--scope` (default FULL):
  - **FULL** — all reviewers, whole diff.
  - **TARGETED** — requirements-verifier + reviewers for the areas named by the caller, on files changed since the last round.
  - **VERIFY** — requirements-verifier + one general-purpose reviewer that checks each FIXED ledger item and the remediation diff.
- `--ledger` — if given, pass it to every reviewer: verify FIXED items (→ VERIFIED / REOPENED), do not re-raise
  DECLINED/ANSWERED items unless the related code changed, and look for regressions caused by fixes.

## 2. Run the gates (deterministic, before any AI review)
Build, full test suite, linters from CLAUDE.md. A failing gate is a 🔴 BLOCKER — still run the reviewers so the
author gets all findings in one round.

## 3. Launch reviewers in parallel (Agent/Task tool, one message, multiple calls)
Give each: base, head, requirement sources, scope, ledger path, and the severity scale.
1. **requirements-verifier** — ALWAYS runs. Every requirement implemented, correctly, with tests; no scope creep.
   Missing/Partial/Wrong/Untested requirement → 🔴 BLOCKER.
2. **performance-reviewer** — 🔴 High → 🟠 MAJOR (🔴 BLOCKER if it breaks a stated non-functional requirement), 🟠 Medium → 🟡 MINOR, 🟡 Low → 💡.
3. **Security** — general-purpose subagent following the `secure-self-review` skill (`${CLAUDE_PLUGIN_ROOT}/skills/secure-self-review/SKILL.md`). Exploitable issue or secret → 🔴 BLOCKER.
4. **Code quality** — `pr-review-toolkit` agents if installed (`code-reviewer`, `pr-test-analyzer`, `silent-failure-hunter`,
   `type-design-analyzer` if types changed); otherwise a general-purpose subagent reviewing against
   `.claude/rules/code-quality.md`, `architecture.md`, `testing.md`. Map their scores onto the severity scale.

## 4. Verify findings before reporting
For every 🔴/🟠 finding, open the cited code and confirm it is real. Drop false positives (say how many). Merge duplicates.

## 5. Report
```
# PR review — <title> (<base>...<head>) — round <N> — scope <FULL|TARGETED|VERIFY>
Verdict: ✅ APPROVE · 🟠 APPROVE WITH COMMENTS · ❌ REQUEST CHANGES

## Gates
Build / Tests / Lint: <results>

## Requirements (requirements-verifier)
<traceability table + unchecked tasks + out-of-scope changes>

## Previous findings (if ledger)
| ID | Was | Now (VERIFIED / REOPENED) | Note |

## New findings
| ID | Sev | Type | Area | Location | Finding | Suggested fix |

## What's good
<brief, specific>
```
Verdict: any 🔴/🟠 open, or any ❓ unanswered → REQUEST CHANGES. Only 🟡/💡 → APPROVE WITH COMMENTS. None → APPROVE.

## 6. Optional: post to GitHub
Only if the user asks: `gh pr review <n> --comment --body-file <report>` (or `--request-changes`). Never approve/merge on your own.
