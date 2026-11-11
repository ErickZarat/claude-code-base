# Changelog

All notable changes to the `eng-standards` plugin. Versions follow semver; the version lives in
`plugins/eng-standards/.claude-plugin/plugin.json`.

## [1.2.0] — 2026-11-10
### Fixed — review-cycle infinite loop (same finding reopened 3×, fixes blocked by the secret guard)
- Secret guard: heuristic checks (`password = "…"`, `user:pass@host` URLs) are skipped in test files, so tests can
  prove credentials don't leak. Real token formats (AWS, GitHub, Stripe, private keys, JWT…) are still blocked
  everywhere. Values containing fake/mock/test/sample count as placeholders.
- Secret guard messages show the flagged line (secret redacted) and tell Claude not to retry with reworded content.
- review-cycle: findings carry a fingerprint (component · problem class) matched against all ledger rows, so
  variants of a known problem reuse the ID instead of becoming new findings. `Seen` count in the ledger.
  2nd occurrence → fix the root cause across all variants; 3rd → stop and ask. A hook/tool blocking the same fix
  twice → stop and ask.
- Rule (workflow.md): never reword/obfuscate to get past a hook or guard; same error twice → stop and ask.
  Re-run `/eng-standards:setup` in projects to receive it.

## [1.1.0] — 2026-11-10
### Changed — token usage (reviews were ~79% of usage, driven by subagents)
- Reviewer agents default to cheaper models: `requirements-verifier`, `performance-reviewer` → sonnet
  (were opus); `thorough` depth escalates to opus per call.
- `pr-review` now has depth modes chosen by triage: **quick** (1 reviewer), **standard** (2–3), **thorough** (full fan-out).
  pr-review-toolkit agents only run in thorough.
- Reviewers read one shared **review packet** (`scripts/review_packet.py`: diff, changed files, requirement sources,
  triage) instead of exploring the repo independently.
- Deterministic gates (build, tests, lint, gitleaks, semgrep) run before any reviewer; reviewers don't repeat them.
- `review-cycle`: re-review rounds read only the remediation diff; VERIFY rounds use the new `fix-verifier` (haiku);
  default max rounds 5 → 3; ledger carries state instead of pasted reports.
- `pr-review`, `review-cycle` are manual-only (`disable-model-invocation`) and all skill descriptions shortened
  (< 150 chars) — they're sent on every request.
- Reviewer output is tables only, capped per reviewer.
### Added
- `code-reviewer` agent (quality + security + tests + architecture in one pass) and `fix-verifier` agent.
- Installer gitignores review packets. Validator rejects opus/inherit agent defaults and long skill descriptions.

## [1.0.0] — 2026-11-10
### Added
- Rules template: workflow (no vibe coding), code quality, architecture (ports & adapters), security, TDD testing,
  path-scoped Kotlin/JVM, TypeScript, Python, SQL/migrations rules.
- Skills: `setup`, `bootstrap-project`, `tdd`, `reuse-first`, `interface-first-design`, `plan-change`,
  `secure-self-review`, `definition-of-done`, `pr-review`, `review-cycle`.
- Agents: `requirements-verifier`, `performance-reviewer`.
- `guard_secrets.py` PreToolUse hook: blocks secret-file access, hard-coded secrets, env dumps, force push, hard reset, git clean.
- Manifest-based installer with safe updates (`.eng-new` on local modifications), ignore file, dry run, user mode.
- CI: validation, shellcheck, pytest on Ubuntu + macOS, gitleaks.
