---
name: task
description: Work one GitHub ticket end to end — branch, TDD, DoD, PR titled [ISSUE-n], review cycle. One PR per task.
disable-model-invocation: true
argument-hint: "[issue# | next] [--depth quick|standard|thorough] [--stack]"
---

# Work one ticket → one PR

`SYNC` = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/github_sync.py"` (fallback path: see the epic skill).
`<n>` = ticket number, `<tag>` = `[ISSUE-<n>]`, `<epic>` = the epic number from the ticket body ("Part of #…").
Scope is **this ticket only**. Anything else you discover goes in the final report as a proposed new task.

## 1. Start clean
- `git status` must be clean (except an uncommitted `tasks.md`/`github.json` from `/eng:epic`, which this PR carries). Otherwise ask.
- If this conversation already holds another task's work, tell the user to `/clear` and re-run — one task per context keeps cost down.

## 2. Pick the ticket
- Number given → use it. `next` → `SYNC next --change openspec/changes/<change>` (the active change).
  `none` → every task is done or already has a PR: report the epic status and suggest `/opsx:archive` when all are merged.
- Read only what this task needs: `gh issue view <n> --json title,body`, its entry in `tasks.md`, and from the change
  folder the `proposal.md`, `design.md` and the delta-spec requirements/scenarios this task implements.

## 3. Branch
- `git fetch origin` then `git switch -c "$(SYNC branch --issue <n> --title "<ticket title>")" origin/<default-branch>`.
- **Dependency check:** if the task needs code from an earlier task whose PR is not merged yet, ask the user:
  wait / merge it first, or stack (`--stack`): branch from that PR's branch, open this PR against it, and write
  `Depends on #<pr>` in the body.

## 4. Implement (the usual rules apply)
`tdd` for every behaviour (failing test shown first), `reuse-first` before new code, `interface-first-design` for
anything external. Then mark the task `[x]` in `tasks.md` on this branch.

## 5. Definition of done
Run the `dod` skill. Fix everything it finds before continuing.

## 6. Commit, push, draft PR
- Every commit message starts with the tag: `<tag> <type>(<scope>): <summary>` — e.g. `[ISSUE-43] feat(refunds): reject refunds above order total`.
- `git push -u origin <branch>`
- `gh pr create --draft --base <base> --title "$(SYNC title --issue <n> --type <type> --title "<ticket title without its 1.2 key>")" --body-file <file>`
  with this body:
  ```
  Closes #<n>
  Part of #<epic>

  ## Summary
  ## How it was verified      (test/build/lint results from DoD)
  ## Notes / follow-ups
  ```

## 7. Review cycle on the PR
Follow `${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md` for this PR (depth from `--depth`, else triage — most task PRs
are small and get `quick`). Remediation commits also start with `<tag>`.

## 8. Finish
- Review exited clean → `gh pr ready <pr>` and post ONE short PR comment: verdict, rounds, findings fixed/declined, ledger path.
- Review stopped (escalation, max rounds, blocked fix) → leave the PR as draft and explain what needs a decision.
- Report: PR link, verdict, follow-ups. **Never merge.** Suggest: merge when happy, then `/clear` and `/eng:task next`.
