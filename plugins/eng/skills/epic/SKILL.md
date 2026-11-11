---
name: epic
description: Sync an OpenSpec change to GitHub — a milestone (or parent issue) plus one ticket per task, tagged [TASK-n] in tasks.md.
disable-model-invocation: true
argument-hint: "[change-name] [--tracking milestone|epic|both] [--group-by section] [--dry-run]"
---

# Sync an OpenSpec change to GitHub

Script: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/github_sync.py"` (if the variable is not expanded:
`find ~/.claude/plugins -path '*claude-code-base/eng/*/scripts/github_sync.py' | head -1`). Below: `SYNC`.

**Tracking modes** (`--tracking`):
- `milestone` (default) — one milestone per change (progress bar, due date) + a `change:<name>` label on every ticket.
  Works on free personal accounts.
- `epic` — a parent issue labelled `epic` with the tickets as sub-issues. GitHub's native *Epic* issue type exists only
  for organizations; this is a normal issue playing that role.
- `both` — milestone and parent issue.
A change keeps the mode it was first synced with unless `--tracking` is given.

1. **Preconditions.** `gh auth status` works and the repo has a GitHub remote. Otherwise stop and say what is missing.
2. **Pick the change.** The argument, or the only folder in `openspec/changes/` other than `archive/`. Several → ask.
   If `openspec` is installed, run `openspec validate <change>` and stop on errors.
3. **Spec lint first:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/spec_lint.py" --change openspec/changes/<change>`.
   Any ERROR → stop and suggest `/eng:spec` to fix the change. WARNs → show them and ask whether to continue.
   **Confirm the tasks are approved** — tickets are hard to undo. If the user has not approved `tasks.md` in this
   conversation, show it briefly and ask.
4. **Granularity.** Default: one ticket (and one PR) per task. Task annotations `(after: 1.1; size: S)` become
   "Depends on #n" in the ticket and a `size:S` label; `/eng:task next` respects the order. If most tasks are tiny (one-line chores such as
   "add dependency"), or there are more than ~12, suggest `--group-by section` (one ticket per `## N.` section). Ask once.
5. **Preview:** `SYNC sync --change openspec/changes/<change> [--tracking …] [--group-by section] --dry-run`. Show the list.
6. **Create:** same command without `--dry-run`. Report the milestone / issue links, created ticket numbers and every
   warning (e.g. autolink needs repo admin).
7. **Commit the mapping** (`tasks.md` with `[TASK-n]` tags + `github.json`):
   `[NO-ISSUE] chore(openspec): link <change> tasks to GitHub issues`.
   If the default branch is protected, leave the changes uncommitted — `/eng:task` carries them into the first task's PR.
8. **One-time repo setup** (ask; needs admin):
   - Squash merges titled by the PR so merge commits keep the tag:
     `gh api -X PATCH repos/<owner>/<repo> -F allow_squash_merge=true -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY -F delete_branch_on_merge=true`
   - Suggest making the `PR title` and `PR checklist` checks required in branch protection for the default branch.
9. Next step for the user: `/eng:task next`.

Re-run `/eng:epic` whenever `tasks.md` changes: it only creates tickets for new tasks and refreshes the milestone / epic.
