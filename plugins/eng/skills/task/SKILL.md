---
name: task
description: Work one GitHub ticket end to end — branch, TDD, DoD, PR linked to the issue with checklists, review cycle. One PR per task.
disable-model-invocation: true
argument-hint: "[issue# | next] [--depth quick|standard|thorough] [--stack]"
---

# Work one ticket → one PR

`SYNC` = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/github_sync.py"` (fallback path: see the epic skill).
`<n>` = ticket number, `<tag>` = `[ISSUE-<n>]`. `github.json` in the change folder gives the milestone / epic.
Scope is **this ticket only**. Anything else you discover goes in the PR's *Pending decisions* or the final report.

## 1. Start clean
- `git status` must be clean (except an uncommitted `tasks.md`/`github.json` from `/eng:epic`, which this PR carries). Otherwise ask.
- If this conversation already holds another task's work, tell the user to `/clear` and re-run — one task per context keeps cost down.

## 2. Pick the ticket
- Number given → use it. `next` → `SYNC next --change openspec/changes/<change>` (the active change).
  `none` → every task is done or already has a PR: report the milestone status and suggest `/opsx:archive` when all are merged.
- Read only what this task needs: `gh issue view <n> --json title,body,milestone`, its line in `tasks.md`, and from the
  change folder `proposal.md`, `design.md` and the delta-spec requirements/scenarios this task implements.
- **Write down the acceptance criteria now**: one line per requirement/scenario (WHEN/THEN) this task must satisfy,
  plus the task line itself. These drive the tests and become the PR checklist.

## 3. Branch
- `git fetch origin` then `git switch -c "$(SYNC branch --issue <n> --title "<ticket title>")" origin/<default-branch>`.
- **Dependency check:** if the task needs code from an earlier ticket whose PR is not merged, ask: wait / merge it first,
  or stack (`--stack`): branch from that PR's branch, open this PR against it, write `Depends on #<pr>` in the body.

## 4. Implement
`tdd` for every acceptance criterion (failing test shown first), `reuse-first` before new code,
`interface-first-design` for anything external. Then mark the task `[x]` in `tasks.md` on this branch.
A question only a person can answer (product rule, naming, scope) → don't guess: record it as a pending decision.

## 5. Definition of done
Run the `dod` skill. Fix everything it finds before continuing.

## 6. Commit, push, draft PR linked to the issue
- Every commit message starts with the tag: `<tag> <type>(<scope>): <summary>`.
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
Follow `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` for this PR (depth from `--depth`, else triage — most task PRs
are small and get `quick`). Remediation commits also start with `<tag>`. Questions the review raises that need a
person go into *Pending decisions*.

## 8. Finish
- Update the PR body (`gh pr edit <pr> --body-file <file>`): check every acceptance criterion and DoD item that is now
  proven; leave the rest unchecked — never check something without evidence.
- **Everything checked and review exited clean** → `gh pr ready <pr>`; the `PR checklist` CI job re-verifies it.
  Post ONE short comment: verdict, rounds, findings fixed/declined, ledger path.
- **Anything unchecked** (pending decision, unproven criterion, review escalation) → keep the PR as **draft** and tell
  the user exactly which items are open and who needs to decide. The CI job lists them on the PR too.
- Report: PR link, verdict, open items. **Never merge.** Suggest: merge when happy, then `/clear` and `/eng:task next`.
