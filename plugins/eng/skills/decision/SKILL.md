---
name: decision
description: Use when a design chooses between real alternatives or changes architecture — record it in docs/decisions/ with decisions.py.
---

# Record a decision

When: a choice between real alternatives (storage engine, sync vs async, pagination strategy, library, API shape),
an architecture change, or reversing an earlier decision. Not for obvious or easily reversible details.

1. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/decisions.py" new --title "<decision as a short statement>" [--change <openspec change>] [--supersedes <n>]`
   (fallback path: `find ~/.claude/plugins -path '*claude-code-base/eng/*/scripts/decisions.py' | head -1`).
2. Fill the four sections briefly: **Context** (forces, constraints), **Options considered** (2–4, one line each with
   the main trade-off), **Decision** (one or two sentences), **Consequences** (what gets easier/harder; what would
   make us revisit). Facts only — no invented numbers.
3. Status stays `Proposed` until the user agrees; then set `Accepted`.
4. Link it from the change's `design.md` (and the PR body if one exists). `decisions.py list` shows all records.
