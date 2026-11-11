---
name: review-once
description: One review round of a PR or branch with independent reviewer subagents; severity-ranked findings and a verdict.
disable-model-invocation: true
argument-hint: "[PR# | base branch] [--depth quick|standard|thorough] [--scope FULL|TARGETED|VERIFY] [--ledger path]"
---

# PR review (one round)

Reviewers are subagents (fresh context) so the author never grades its own work. Severity scale:
🔴 BLOCKER · 🟠 MAJOR · 🟡 MINOR · 💡 SUGGESTION · ❓ QUESTION (defined in
`${CLAUDE_PLUGIN_ROOT}/skills/review/SKILL.md`).

**Token rules:** reviewers read ONE shared packet instead of exploring the repo; only the reviewers the change needs
are launched; deterministic tools run first; output is tables only.

## 1. Scope
- PR number → `gh pr view <n> --json title,body,baseRefName,headRefName`; fetch/check out the head. Else base = given branch or `main`.
- Packet dir: `.reviews/<branch>/` (or `openspec/changes/<change>/reviews/<branch>/` when an OpenSpec change is active).

## 2. Build the packet (once per round)
```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_packet.py" --base <base> --out <dir>/packet.md   [--since <sha> for re-review rounds]
```
If `${CLAUDE_PLUGIN_ROOT}` is not expanded: `find ~/.claude/plugins -path '*claude-code-base/eng/*/scripts/review_packet.py' | head -1`.
Read only its **Triage** section yourself; reviewers read the whole packet. For a PR, always append the PR body to the packet
under `## PR description` — its *Acceptance criteria* checklist is a requirement source, and `requirements-verifier`
must confirm each checked item really has a passing test (a checked box without evidence is a 🔴 BLOCKER).

## 3. Deterministic gates (cheap — before any reviewer)
Build, tests, lint (commands from CLAUDE.md); `gitleaks detect --no-banner --redact` and `semgrep scan --config auto --error`
if installed. A failing gate is a 🔴 BLOCKER. Pass a one-line result per gate to the reviewers.

## 4. Pick reviewers by depth
Depth = `--depth` if given, else the packet's suggested depth — but never below the project's minimum: a
`Minimum review depth: <quick|standard|thorough>` line in CLAUDE.md (absent = quick).
Launch the chosen reviewers in ONE message (parallel),
each with: packet path, gate results, ledger path (if any), scope. With a ledger, tell reviewers: match every finding
against ALL ledger rows by fingerprint (component · problem class) and reuse the ID — variants of a known problem are
not new findings.

| Depth | Reviewers | Typical use |
|---|---|---|
| **quick** | `code-reviewer` only — also asked to check the change against the requirement sources | Small, low-risk diffs (≤ 50 lines, no security triggers) |
| **standard** (default) | `requirements-verifier` + `code-reviewer` + `performance-reviewer` *only if triage says performance: yes* | Normal PRs |
| **thorough** | standard + `performance-reviewer` always + general-purpose security subagent following `${CLAUDE_PLUGIN_ROOT}/skills/secure-self-review/SKILL.md` + `pr-review-toolkit` agents if installed; run `requirements-verifier` and `code-reviewer` with `model: opus` | Auth, payments, migrations, public APIs, big refactors |

**Scope** (set by review): FULL = as above · TARGETED = `requirements-verifier` + only the reviewers for the
areas that had MAJOR fixes, packet built with `--since` · VERIFY = `fix-verifier` only, packet built with `--since`.

## 5. Confirm before reporting
For each 🔴/🟠 finding, read only the cited lines and confirm it's real. Drop false positives (count them). Merge duplicates.

## 6. Report (tables, no essays)
```
# Review — <title> (<range>) — round <N> — depth <d> — scope <s>
Verdict: ✅ APPROVE · 🟠 APPROVE WITH COMMENTS · ❌ REQUEST CHANGES
Gates: build ✅ tests ✅ lint ✅ gitleaks ✅ semgrep n/a
Reviewers: <list> · false positives dropped: <n>

## Coverage                — what this round did and did NOT check, so the user can judge it
Depth: <d> (<why: --depth / triage: N lines, security yes/no / project minimum>)
Reviewers run: <agent (model)>, …          Skipped: <agent — reason, e.g. "performance — triage found no data/loop/I/O changes">
Files: <reviewed>/<changed> (<list any not reviewed: truncated diff, generated, binary>)
Requirement sources: <files / PR body / none>
Not checked: <anything outside this depth — e.g. "no dedicated security reviewer (quick)", "semgrep not installed">
Deeper option: `--depth <next level>` adds <reviewers>

## Requirements            (requirements-verifier table, or code-reviewer's check in quick mode)
## Previous findings       | ID | Was | Now | Note |          (if ledger)
## New findings            | ID | Area | Location | Finding | Proposed fix |     (every finding listed — none summarised away)
IDs: `R<round>-<BLK|MAJ|MIN|Q|S>-<n>`, numbered after the ledger's highest number (see the review skill).
```
Verdict: any 🔴/🟠 open or ❓ unanswered → REQUEST CHANGES · only 🟡/💡 → APPROVE WITH COMMENTS · none → APPROVE.

Standalone (not inside the review cycle): end with the report and ask whether to fix the findings
(that continues as the review cycle from its checkpoint) — never start fixing on your own.

Post to GitHub only if the user asks (`gh pr review <n> --comment --body-file <report>`). Never approve or merge.
