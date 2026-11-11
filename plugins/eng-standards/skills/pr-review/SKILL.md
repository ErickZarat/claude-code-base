---
name: pr-review
description: One review round of a PR or branch with independent reviewer subagents; severity-ranked findings and a verdict.
disable-model-invocation: true
argument-hint: "[PR# | base branch] [--depth quick|standard|thorough] [--scope FULL|TARGETED|VERIFY] [--ledger path]"
---

# PR review (one round)

Reviewers are subagents (fresh context) so the author never grades its own work. Severity scale:
🔴 BLOCKER · 🟠 MAJOR · 🟡 MINOR · 💡 SUGGESTION · ❓ QUESTION (defined in
`${CLAUDE_PLUGIN_ROOT}/skills/review-cycle/SKILL.md`).

**Token rules:** reviewers read ONE shared packet instead of exploring the repo; only the reviewers the change needs
are launched; deterministic tools run first; output is tables only.

## 1. Scope
- PR number → `gh pr view <n> --json title,body,baseRefName,headRefName`; fetch/check out the head. Else base = given branch or `main`.
- Packet dir: `.reviews/<branch>/` (or `openspec/changes/<change>/reviews/` when an OpenSpec change is active).

## 2. Build the packet (once per round)
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_packet.py" --base <base> --out <dir>/packet.md   [--since <sha> for re-review rounds]
```
If `${CLAUDE_PLUGIN_ROOT}` is not expanded: `find ~/.claude/plugins -path '*eng-standards*/scripts/review_packet.py' | head -1`.
Read only its **Triage** section yourself; reviewers read the whole packet. For a PR, append the PR body to the packet
under `## PR description` if the packet lists no requirement sources.

## 3. Deterministic gates (cheap — before any reviewer)
Build, tests, lint (commands from CLAUDE.md); `gitleaks detect --no-banner --redact` and `semgrep scan --config auto --error`
if installed. A failing gate is a 🔴 BLOCKER. Pass a one-line result per gate to the reviewers.

## 4. Pick reviewers by depth
Depth = `--depth` if given, else the packet's suggested depth. Launch the chosen reviewers in ONE message (parallel),
each with: packet path, gate results, ledger path (if any), scope.

| Depth | Reviewers | Typical use |
|---|---|---|
| **quick** | `code-reviewer` only — also asked to check the change against the requirement sources | Small, low-risk diffs (≤ 50 lines, no security triggers) |
| **standard** (default) | `requirements-verifier` + `code-reviewer` + `performance-reviewer` *only if triage says performance: yes* | Normal PRs |
| **thorough** | standard + `performance-reviewer` always + general-purpose security subagent following `${CLAUDE_PLUGIN_ROOT}/skills/secure-self-review/SKILL.md` + `pr-review-toolkit` agents if installed; run `requirements-verifier` and `code-reviewer` with `model: opus` | Auth, payments, migrations, public APIs, big refactors |

**Scope** (set by review-cycle): FULL = as above · TARGETED = `requirements-verifier` + only the reviewers for the
areas that had MAJOR fixes, packet built with `--since` · VERIFY = `fix-verifier` only, packet built with `--since`.

## 5. Confirm before reporting
For each 🔴/🟠 finding, read only the cited lines and confirm it's real. Drop false positives (count them). Merge duplicates.

## 6. Report (tables, no essays)
```
# Review — <title> (<range>) — round <N> — depth <d> — scope <s>
Verdict: ✅ APPROVE · 🟠 APPROVE WITH COMMENTS · ❌ REQUEST CHANGES
Gates: build ✅ tests ✅ lint ✅ gitleaks ✅ semgrep n/a
Reviewers: <list> · false positives dropped: <n>

## Requirements            (requirements-verifier table, or code-reviewer's check in quick mode)
## Previous findings       | ID | Was | Now | Note |          (if ledger)
## New findings            | ID | Sev | Area | Location | Finding | Fix |
```
Verdict: any 🔴/🟠 open or ❓ unanswered → REQUEST CHANGES · only 🟡/💡 → APPROVE WITH COMMENTS · none → APPROVE.

Post to GitHub only if the user asks (`gh pr review <n> --comment --body-file <report>`). Never approve or merge.
