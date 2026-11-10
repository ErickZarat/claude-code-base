# claude-code-base

Engineering standards for Claude Code, packaged as a plugin marketplace so every project gets the same behaviour:
**no vibe coding, TDD, reuse before writing, interface-first design, no leaked secrets or backdoors, and iterative
PR review until every requirement is implemented and tested.** Works with or without OpenSpec.

## Add it to any project (2 steps)

**Once per machine** — install the plugin at user scope (skills, reviewer agents and the secret guard then work everywhere):
```text
/plugin marketplace add ErickZarat/claude-code-base
/plugin install eng-standards@claude-code-base        # choose "user" scope
/plugin install security-guidance@claude-plugins-official
```
> Private repo: Claude Code uses your git credentials (`gh auth login` or SSH) to fetch it.

**In each project** — install the per-project files (rules, CLAUDE.md, settings, pre-commit):
```text
/eng-standards:setup
```
It previews the changes (dry run), installs, and on first install runs `bootstrap-project` to fill in CLAUDE.md,
prune unused language rules and optionally set up OpenSpec. Commit the result: the project's `.claude/settings.json`
declares this marketplace and plugin, so teammates who trust the folder are prompted to install them.

Without the plugin (CI, scripts): `git clone` this repo and run `./install.sh /path/to/project` (or `--user`, `--dry-run`).

## Updating
1. Change something here → bump `version` in `plugins/eng-standards/.claude-plugin/plugin.json`, add a CHANGELOG entry, push.
2. On each machine: `/plugin marketplace update claude-code-base` (skills, agents and hooks update immediately).
3. In each project: `/eng-standards:setup` again to sync rules. The installer keeps a checksum manifest:
   - rules you never touched → updated
   - rules you customised → kept; the new version lands next to them as `<file>.eng-new` for you to merge
   - `CLAUDE.md` and `settings.json` → project-owned, never overwritten
   - paths listed in `.claude/.eng-standards-ignore` → never reinstalled
   - installed version recorded in `.claude/.eng-standards-version`

## What's inside

| Piece | What it does |
|---|---|
| **Rules** (`template/.claude/rules/`) | workflow (read → plan → small verified steps), code quality (names, comments, DRY, errors), architecture (ports & adapters, DI), security (secrets, no backdoors, input validation), testing (TDD mandatory), path-scoped Kotlin/JVM · TypeScript · Python · SQL rules |
| `/eng-standards:setup` | Install/update project files |
| `bootstrap-project` | Detect stack, fill CLAUDE.md, prune rules, OpenSpec setup |
| `tdd` | Red → green → refactor with real test output as evidence |
| `reuse-first` | Search the codebase before creating anything |
| `interface-first-design` | Port + adapter for anything external or replaceable |
| `plan-change` | Written plan for approval (projects without OpenSpec) |
| `secure-self-review` | gitleaks / semgrep / audit + manual security checklist on the diff |
| `definition-of-done` | Build, tests, lint, diff review, honest summary |
| `/eng-standards:pr-review` | One review round: gates + 4 parallel reviewers → severity-ranked findings |
| `/eng-standards:review-cycle` | Review → remediation → re-review rounds until exit criteria are met |
| `requirements-verifier` agent | Requirement → code → test traceability; missing / wrong / untested / scope creep |
| `performance-reviewer` agent | Complexity, N+1, indexes, memory, blocking I/O, leaks |
| Secret guard hook | Blocks reading `.env`/keys, writing secrets, `printenv`, force push, hard reset, `git clean -f` |

### Review cycle
```
Round 1  FULL review ──► findings (🔴 BLOCKER 🟠 MAJOR 🟡 MINOR 💡 SUGGESTION ❓ QUESTION) ──► ledger
   ▼
Remediation  fixes with TDD, answers questions, declines minors with reasons
   ▼
Next round by highest severity fixed:  🔴 → FULL   🟠 → TARGETED   🟡/💡/❓ → VERIFY
   (requirements + test coverage are checked in EVERY round; missing tests are always a BLOCKER)
   ▼
Exit: gates green · every requirement Done & tested · no open 🔴/🟠/❓ · every fix verified by a reviewer
Stops and asks you: 5 rounds · same finding reopened twice · disagreement on 🔴/🟠 · product decision needed
```

### Security layers
rules (intent) → secret-guard hook + permission deny-list (deterministic) → security-guidance plugin (model review)
→ gitleaks pre-commit → CI gitleaks.

## Recommended extra plugins
```text
/plugin install pr-review-toolkit@claude-plugins-official   # used by pr-review for code-quality checks
/plugin install code-review@claude-plugins-official
/plugin marketplace add trailofbits/skills                  # semgrep, supply-chain-risk-auditor, ...
```
Use one planning system per project: OpenSpec **or** superpowers, not both.

## Developing this repo
See `CLAUDE.md`. Quick check: `python3 scripts/validate.py && pytest -q`.
