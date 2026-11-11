# Workflow — no vibe coding

## Before writing code
- Read the relevant code first. Never edit a file you have not read in this session.
- Restate the goal in one or two sentences and list the files you expect to touch.
- If requirements, inputs, edge cases or acceptance criteria are unclear, ASK. Do not invent behaviour.
- Search for existing code that already solves part of the problem (see `reuse-first` skill).
- For anything bigger than a single-file fix, produce a plan first (OpenSpec change or `plan-change` skill)
  and wait for approval.

## While writing code
- Follow TDD (`tdd` skill): a failing test exists before any production logic is written.
- Work in small, reviewable steps. One concern per change.
- Change only what the task needs. No drive-by refactors, renames or reformatting of unrelated code;
  propose them separately instead.
- Do not add dependencies, frameworks or new patterns without stating why the existing ones are insufficient.
- Do not leave placeholders, `TODO` stubs, mock data or commented-out code in production paths.
  If something cannot be finished, stop and say so explicitly.
- Never fake success: do not hard-code values to make tests pass, skip or delete failing tests,
  or weaken assertions. Fix the cause or report it.
- If a hook, permission rule or guard blocks an action, never reword or obfuscate to get around it.
  Fix what it flagged, or stop and tell the user. Same error twice in a row → stop and ask.

## After writing code
- Run the project's build, tests and linter (commands in CLAUDE.md). Report real output, not assumptions.
- Run the `dod` skill before saying the task is complete.
- Summarize: what changed, why, how it was verified, and any follow-ups or risks.

## Git
- Small commits with clear messages (Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Working on a GitHub ticket: one branch and one PR per ticket; every commit message and the PR title start with
  `[ISSUE-<n>] ` (e.g. `[ISSUE-43] feat(refunds): …`); the PR body has `Closes #<n>`. No ticket: `[NO-ISSUE] `.
- Every task PR gets `/eng:dod` and the review cycle before it is marked ready. Never merge on your own.
- Never force-push, hard-reset, or rewrite shared history. Never commit generated secrets, `.env` files or build output.
