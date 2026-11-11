---
name: task
description: Work one GitHub ticket end to end — branch, TDD, DoD, PR linked to the issue with checklists, review cycle. One PR per task.
disable-model-invocation: true
argument-hint: "[issue# | next | new \"title\" --bug|--feature] [--depth standard|thorough|quick] [--stack] [--auto]"
---

# Work one ticket → one PR

`SYNC` = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/github_sync.py"` (fallback path: see the epic skill).
`<n>` = ticket number, `<tag>` = `$(SYNC tag --issue <n>)` — `[<KIND>-<n>]` where KIND comes from the issue's type, else
its type label (bug → BUG, feature/enhancement → FEATURE, task → TASK, story → STORY, chore → CHORE, spike → SPIKE),
else ISSUE. Look it up once and reuse it. `github.json` in the change folder gives the milestone / epic.
Scope is **this ticket only**. Anything else you discover goes in the PR's *Pending decisions* or the final report.

## 1. Start clean
- `git status` must be clean (except an uncommitted `tasks.md`/`github.json` from `/eng:epic`, which this PR carries). Otherwise ask.
- If this conversation already holds another task's work, tell the user to `/clear` and re-run — one task per context keeps cost down.

## 2. Pick the ticket
- Number given → use it. `next` → `SYNC next --change openspec/changes/<change>` (the active change).
  It skips tickets whose dependencies (`after:` in tasks.md) are not merged yet and prints `blocked: #x waits for #y`.
  `none` → nothing is ready: show what is blocked or in review; when everything is merged suggest
  `/eng:spec --before-archive`, then `/opsx:archive`.
- `new "<title>" --bug|--feature` → create the ticket first: `gh issue create --title "<title>" --label bug|feature
  --body "<what happens, expected behaviour, steps to reproduce>"` (ask for anything missing), then continue with it.
- Read only what this task needs: `gh issue view <n> --json title,body,milestone`, its line in `tasks.md`, and from the
  change folder `proposal.md`, `design.md` and the delta-spec requirements/scenarios this task implements.
- **Write down the acceptance criteria now**: one line per requirement/scenario (WHEN/THEN) this task must satisfy,
  plus the task line itself, with its scenario ID (`python3 <scripts>/trace.py --change openspec/changes/<change> --list`).
  These drive the tests and become the PR checklist.

### Lite path — the ticket belongs to no OpenSpec change (bugs, small fixes)
No `github.json` lists this issue → no proposal needed:
- Acceptance criteria come from the issue body (`## Acceptance criteria` or the expected behaviour); confirm 2–5
  criteria with the user if the issue is vague.
- **Bug:** first a failing test that reproduces it (`tdd`), then the fix.
- **Specs:** search `openspec/specs/` for the behaviour. Fix restores specified behaviour → no spec change; mark the
  regression test `spec: <capability>/<scenario>`. Fix *changes* specified behaviour → stop and ask: open an OpenSpec
  change (`/opsx:propose`) or let the user approve updating the spec in this PR.
- Milestone/epic lines are omitted from the PR body; everything else in this skill applies.

## 3. Claim, then branch
- **Claim first:** `SYNC claim --issue <n>` assigns the ticket to you, so a teammate's `next` skips it. If it is
  assigned to someone else, stop and tell the user (`--force` only if they confirm the teammate handed it over).
- `git fetch origin` then `git switch -c "$(SYNC branch --issue <n> --title "<ticket title>")" origin/<default-branch>` (e.g. `bug-10-null-total`).
- **Blocked:** if `next` printed `blocked: …`, or the task needs code from a ticket whose PR is not merged, offer:
  **take another ready ticket** (`SYNC status`) or **stack** (`--stack`): branch from that PR's branch, open this PR
  against it, write `Depends on #<pr>` in the body. When that PR is merged and its branch deleted, GitHub retargets
  this PR to the default branch automatically.
- **Dependency discovered while working** (the task turns out to need another ticket first):
  `SYNC block --issue <n> --by <other>` — recorded on GitHub only; never edit `tasks.md` for it. Then wait or stack.

## 3b. Plan this ticket (before the first test — 10–15 lines, shown to the user)
Most review MAJORs are design problems that are cheap to avoid here. Write:
- **Files** to touch, and the **existing code to reuse** (`path:Symbol`, from `reuse-first`) — plus the matching
  reference pattern from CLAUDE.md *Patterns*.
- **Ports/adapters** involved (`interface-first-design`), and any contract change (backwards compatible?).
- **Behaviours = tests**, in TDD order: each acceptance criterion with its scenario ID, plus edge and failure cases
  (empty, invalid, not found, limits, permission, downstream failure/timeout).
- **NFR targets** that apply (latency, volume, security, observability) and how the code meets them
  (pagination, batching, timeouts, indexes).
- **Open questions** → ask now, not in review.
Continue straight away unless there is an open question or the plan deviates from the spec.

## 4. Implement
`tdd` for every acceptance criterion (failing test shown first) — each test carries a marker comment with the
scenario it proves (`// spec: billing/refund-above-total-is-rejected`); `reuse-first` before new code,
`interface-first-design` for anything external; the `decision` skill when you choose between real alternatives;
contract changes (.proto/OpenAPI/events) stay backwards compatible unless the spec says otherwise.
Do **not** edit `tasks.md` in a task PR (parallel PRs would conflict on it): the merged PR closes the ticket, and
`/eng:epic` / `/eng:status` tick closed tasks in one commit.
A question only a person can answer (product rule, naming, scope) → don't guess: record it as a pending decision.

## 5. Definition of done (includes the self-check)
Run the `dod` skill — it runs the gates and the `self-check` (the reviewers' checklist on your own diff). Fix
everything before opening the PR: every finding you fix here is a review round you don't pay for.

## 6. Commit, push, draft PR linked to the issue
- Every commit message starts with the tag: `<tag> <type>(<scope>): <summary>` — e.g. `[BUG-10] fix(refunds): handle null total`.
- `git push -u origin <branch>`
- Write the body following the project's `.github/pull_request_template.md` (create it from the structure below if missing):
  ```
  Closes #<n>
  Part of milestone: <milestone title>        (and/or "Part of #<epic>" in epic mode)

  ## Summary
  ## Acceptance criteria                       one item per criterion from step 2
  - [x] <criterion> — `<TestClass#test name>`  checked ONLY when a passing test proves it
  - [ ] <criterion>                            unchecked = not done or not proven
  ## Definition of Done                        the template's items; check each from the real DoD results
  ## Pending decisions                         "- [ ] <question> (who decides)" or "None"
  ## How it was verified
  ```
- `gh pr create --draft --base <base> --title "$(SYNC title --issue <n> --type <type> --title "<ticket title without its 1.2 key>")" --body-file <file> --milestone "<milestone title>" --label task --label "change:<change>"`
  (`Closes #<n>` links the PR to the issue — it shows under the issue's *Development* and closes it on merge.)

## 7. Review cycle on the PR
Follow `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` for this PR (depth from `--depth`, else triage and the project
minimum — `standard` by default: every dedicated reviewer runs, also on small task PRs). It **stops after each review round** to show the findings and
ask which to fix; continue the task only after the user answers. Pass `--auto` only if the user asked for an
unattended run. Remediation commits also start with `<tag>`. Questions the review raises that need a
person go into *Pending decisions*.

## 8. Finish
- Update the PR body (`gh pr edit <pr> --body-file <file>`): check every acceptance criterion and DoD item that is now
  proven; leave the rest unchecked — never check something without evidence.
- **Everything checked and review exited clean** → `gh pr ready <pr>`; the `PR checklist` CI job re-verifies it.
  Post ONE short comment: verdict, rounds, findings fixed/declined, ledger path.
- **Anything unchecked** (pending decision, unproven criterion, review escalation) → keep the PR as **draft** and tell
  the user exactly which items are open and who needs to decide. The CI job lists them on the PR too.
- Report: PR link, verdict, open items. **Never merge.** Suggest: merge when happy, then `/clear` and `/eng:task next`.
