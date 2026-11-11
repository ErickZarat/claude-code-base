---
name: retro
description: Learn from past reviews — find review findings that keep recurring across PRs and propose one-line rules to prevent them.
disable-model-invocation: true
argument-hint: "[--min N]"
---

# Retro: turn recurring review findings into rules

1. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/findings_report.py" $ARGUMENTS` (fallback path: see the spec skill).
   It reads every review ledger (archived changes included) and lists totals by severity/area and **recurring problem
   classes** (default: ≥ 3 findings in ≥ 2 ledgers).
   It also prints **first-time quality**: average rounds per PR, clean first rounds, first-round findings per 100
   changed lines — compare with the last retro to see whether the plan + self-check steps are working.
2. For each recurring class, open one or two of its ledger rows to understand the pattern, then draft **one** precise
   rule line that would have prevented it — or, when a tool can detect it (naming, unused code, complexity, missing
   timeout, string-built SQL…), a **lint/semgrep rule** instead, which costs no review tokens ever again (e.g. "Every repository query that can return many rows is paginated —
   `findAll` without a limit is not allowed"). Skip classes an existing rule in `.claude/rules/` already covers —
   say so instead, and point at why it was missed (rule too vague? wrong file?).
3. Show the table `problem class · count · proposed rule · target file` and ask which to add. Never add rules unasked.
4. Approved rules go in `.claude/rules/learned.md` (project-owned — `/eng:setup` never overwrites it), one line each,
   with the date and problem class as a trailing comment. Create the file with a `# Learned rules` heading if missing.
5. If a rule would help every project, suggest proposing it upstream in claude-code-base.
