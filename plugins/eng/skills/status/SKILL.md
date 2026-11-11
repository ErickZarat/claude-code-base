---
name: status
description: Team board for an OpenSpec change — who is on which ticket, what is in review, blocked (and by what) or ready to start.
disable-model-invocation: true
argument-hint: "[change-name]"
---

# Status board

`SYNC` = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/github_sync.py"` (fallback: `find ~/.claude/plugins -path '*claude-code-base/eng/*/scripts/github_sync.py' | head -1`).

1. Change = the argument, or every folder in `openspec/changes/` except `archive/` that has a `github.json`.
2. Run `SYNC status --change openspec/changes/<change>` and show its output as is:
   ✅ done · 👀 in review (author, PR) · 🔨 in progress (assignee or draft PR) · ⛔ blocked (waits for #n) · 🟢 ready.
   Dependencies come from `tasks.md` (`after:`), native GitHub "blocked by" links and `Depends on #n` lines.
3. Add at most three lines of advice, only when they apply:
   - a ⛔ ticket waits on a 👀 PR → reviewing/merging that PR unblocks it (name both);
   - 🟢 tickets exist and someone is idle → `/eng:task next`;
   - the same person holds several 🔨 tickets while 🟢 ones wait → suggest handing one over.
4. If closed tickets are still unticked in `tasks.md`, offer `SYNC sync --change …` to tick them (one commit).
Read-only otherwise: never assign, unblock or edit anything from this skill.
