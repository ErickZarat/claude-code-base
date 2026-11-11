---
name: spec
description: Check an OpenSpec change is ready — spec lint, scenario IDs for tests, ambiguity questions; with --before-archive, every scenario tested.
disable-model-invocation: true
argument-hint: "[change-name] [--before-archive]"
---

# Spec check

`S` = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts"` (fallback: `find ~/.claude/plugins -path '*claude-code-base/eng/*/scripts' -type d | head -1`).
Change = the argument, or the only folder in `openspec/changes/` other than `archive/` (several → ask).

## Before implementing (default) — run after `/opsx:propose`, before `/eng:epic`
1. `python3 $S/spec_lint.py --change openspec/changes/<change>` — deterministic: missing scenarios / WHEN / THEN,
   vague wording, no error cases, requirements without a task, missing *Non-functional requirements*, task
   dependency cycles, L-sized tasks.
2. Read `proposal.md`, the delta specs and `tasks.md` **once** and add what a script can't see — max 10 items:
   ambiguous behaviour, contradictions between artifacts, missing edge cases, unstated limits, contract changes without
   a *Contracts* section, a design choice that deserves a decision record. Phrase each as a question with a suggested answer.
3. Show: lint ERRORs, WARNs, your questions — then ask the user: **fix all** · **choose** · **leave as is**. Never edit
   artifacts before they answer. Fix with OpenSpec's own flow (edit the artifacts), then re-run step 1.
4. When lint has no ERROR: `python3 $S/trace.py --change openspec/changes/<change> --list` and show the scenario IDs —
   tests will carry `spec: <id>` markers. Next: `/eng:epic`.

## `--before-archive` — run before `/opsx:archive`
1. Every task in `tasks.md` is `[x]`, and every ticket of the change is closed (`gh issue list --label "change:<change>" --state open`).
2. `python3 $S/trace.py --change openspec/changes/<change> --fail-untested` — every scenario has a test. Report
   stale markers too.
3. `python3 $S/spec_lint.py --change openspec/changes/<change>` — no ERROR.
4. All green → suggest `/opsx:verify` (if enabled) then `/opsx:archive`. Anything missing → list it; do not archive.
