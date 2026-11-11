---
name: self-check
description: Use after implementing and before opening or updating a PR — run gates, then walk your own diff with the reviewers' checklist and fix what you find.
---

# Self-check (author side, same checklist as the reviewers)

Goal: the review cycle should find nothing you could have found yourself. Cheap: same session, no subagents.

1. **Deterministic first** (commands from CLAUDE.md): build, tests, lint/format, static analysis (`semgrep` if
   configured), `gitleaks` if installed. Fix failures before anything else — never hand failing gates to review.
2. **Packet hints:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_packet.py" --base <default-branch> --out .reviews/<branch>/packet.md`
   and read only its *Dynamic SQL candidates* and *Contract changes* sections. If the change belongs to an OpenSpec
   change: `trace.py --change openspec/changes/<change>` for this task's scenarios.
3. **Walk the diff once** (`git diff <default-branch>...HEAD`) against `${CLAUDE_PLUGIN_ROOT}/checklists/self-check.md`
   (fallback: `find ~/.claude/plugins -path '*claude-code-base/eng/*/checklists/self-check.md' | head -1`).
   Fix every hit with the usual rules (a bug → failing test first). Don't re-read unchanged files.
4. Re-run the gates if anything changed.
5. Report one line: `Self-check: fixed <n> — <short list>` (or `clean`). Anything you could not fix (needs a decision)
   goes to the PR's *Pending decisions*.
