---
name: self-check
description: Use after each task's commit — gates, mutation tests on touched files, a quick look at the task diff. The PR-level check is the pre-reviewer agent (dod).
---

# Self-check — light, after each task (same session, no subagents)

Goal: catch the mechanical problems while the diff is small. The whole-PR check with fresh eyes is the
`pre-reviewer` agent, launched once per PR by `dod`.

1. **Deterministic first** (commands from CLAUDE.md): build, tests, lint/format, static analysis (`semgrep` if
   configured), `gitleaks` if installed. Fix failures before anything else — never hand failing gates to review.
2. **Packet hints:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_packet.py" --base <default-branch> --out .reviews/<branch>/packet.md`
   and read only its *Dynamic SQL candidates* and *Contract changes* sections. If the change belongs to an OpenSpec
   change: `trace.py --change openspec/changes/<change>` for this task's scenarios.
3. **Mutation tests** on the files this task touched (the *Mutation tests* command in CLAUDE.md — Stryker for
   TS/JS, PIT for JVM, mutmut for Python). A surviving mutant = a test that proves nothing: strengthen the test
   (never delete the code to kill it). No command configured → say so in the report.
4. **Walk this task's diff** (`git show HEAD`, or `git diff <default-branch>...HEAD` when run for the whole PR) against `${CLAUDE_PLUGIN_ROOT}/checklists/self-check.md`
   (fallback: `find ~/.claude/plugins -path '*claude-code-base/eng/*/checklists/self-check.md' | head -1`).
   Fix every hit with the usual rules (a bug → failing test first). Don't re-read unchanged files.
5. Re-run the gates if anything changed.
6. Report one line: `Self-check: fixed <n> — <short list>` (or `clean`). Anything you could not fix (needs a decision)
   goes to the PR's *Pending decisions*.
