# Changelog

All notable changes to the `eng-standards` plugin. Versions follow semver; the version lives in
`plugins/eng-standards/.claude-plugin/plugin.json`.

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
