---
name: dod
description: Use before saying a coding task is done, committing, or opening a PR: build, tests, lint, diff and security checks, honest summary.
---

# Definition of done

A task is NOT done until every item below passes or is explicitly reported as failing.

## 1. Verify (use the commands in CLAUDE.md — never guess)
- [ ] Build/compile succeeds.
- [ ] Tests pass — run the relevant tests, then the full suite if it is reasonably fast.
- [ ] Linter/formatter/type-checker clean for changed files.
Paste the real result (pass/fail counts or the error), not "should work".

## 2. Self-check
- [ ] Per task (during `/eng:task`): the light `self-check` — gates, mutation tests on touched files, a quick look
      at the task's diff.
- [ ] **Before opening or updating the PR — once per PR, not per task:**
  1. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pr_size.py" --base <default-branch>` — over budget → stop, show the
     breakdown and propose how to split the PR (one PR per part). Don't open an oversized PR without the user's OK.
  2. PRs over ~150 changed lines: build the packet (`review_packet.py --base <default-branch> --out
     .reviews/<branch>/packet.md`) and launch the **`pre-reviewer`** agent with the packet path, the ticket plan (with
     its *Out of scope*) and the ledger path. Record its table in the ledger as `## Round 0 — pre-review`.
     Smaller PRs: the light self-check over the whole diff is enough.
  3. Fix every BLK/MAJ/MIN it found (bugs → failing test first; S optional), re-run the gates, mark rows FIXED.
     Its findings are yours to fix, not a review round — no checkpoint, no re-run of the pre-reviewer.
- [ ] TDD was followed: every new behaviour has a test that was seen failing before the code existed.
- [ ] Every requirement / acceptance criterion is implemented and tested (for OpenSpec scenarios: `spec:` markers).
- [ ] Docs/README/`.env.example`/OpenSpec specs updated if behaviour or configuration changed.

## 3. Security
Covered by the self-check (its gates run gitleaks/semgrep; its Security section is the secure-self-review checklist).
Run the full `secure-self-review` skill only when the change touches auth, secrets, crypto or payment flows.

## 4. Summary to the user
```
Done: <one line>
Changed: <files / modules>
Verified: <build/test/lint results>
Security: <scan results or "tools not installed — manual review only">
Follow-ups / risks: <or "none">
```
If anything failed or could not be verified, say so plainly at the top instead of reporting success.
When a PR exists or is about to be opened, map these results onto its *Definition of Done* checklist: check only the
items you just verified; leave the others unchecked.
