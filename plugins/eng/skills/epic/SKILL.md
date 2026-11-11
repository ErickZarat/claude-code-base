---
name: epic
description: Sync an OpenSpec change to GitHub — an epic issue plus one linked ticket per task, tagged [ISSUE-n] in tasks.md.
disable-model-invocation: true
argument-hint: "[change-name] [--group-by section] [--dry-run]"
---

# Sync an OpenSpec change to a GitHub epic

Script: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/github_sync.py"` (if the variable is not expanded:
`find ~/.claude/plugins -path '*claude-code-base/eng/*/scripts/github_sync.py' | head -1`). Below: `SYNC`.

1. **Preconditions.** `gh auth status` works and the repo has a GitHub remote. Otherwise stop and say what is missing.
2. **Pick the change.** The argument, or the only folder in `openspec/changes/` other than `archive/`. Several → ask.
   If `openspec` is installed, run `openspec validate <change>` and stop on errors.
3. **Confirm the tasks are approved** — tickets are hard to undo. If the user has not approved `tasks.md` in this
   conversation, show it briefly and ask.
4. **Granularity.** Default: one ticket (and one PR) per task. If most tasks are tiny (one-line chores such as
   "add dependency"), or there are more than ~12, suggest `--group-by section` (one ticket per `## N.` section). Ask once.
5. **Preview:** `SYNC sync --change openspec/changes/<change> [--group-by section] --dry-run`. Show the list.
6. **Create:** same command without `--dry-run`. Report the epic URL, created ticket numbers and every warning
   (e.g. sub-issues unsupported → tickets are still listed in the epic checklist; autolink needs repo admin).
7. **Commit the mapping** (`tasks.md` with `[ISSUE-n]` tags + `github.json`):
   `[ISSUE-<epic>] chore(openspec): link <change> tasks to GitHub issues`.
   If the default branch is protected, leave the changes uncommitted — `/eng:task` carries them into the first task's PR.
8. **One-time repo setup** (ask; needs admin) so merge commits keep the tag:
   `gh api -X PATCH repos/<owner>/<repo> -F allow_squash_merge=true -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY -F delete_branch_on_merge=true`
9. Next step for the user: `/eng:task next`.

Re-run `/eng:epic` whenever `tasks.md` changes: it only creates tickets for new tasks and refreshes the epic checklist.
