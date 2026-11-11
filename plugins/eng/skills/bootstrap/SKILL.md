---
name: bootstrap
description: Adapt the eng setup to this repo: fill CLAUDE.md, prune language rules, optional OpenSpec.
disable-model-invocation: true
---

# Bootstrap this project

## 1. Detect the stack (read, do not guess)
Look for: `build.gradle(.kts)`, `pom.xml`, `settings.gradle*`, `package.json` + lock file, `pyproject.toml`/`requirements*.txt`,
`go.mod`, `Cargo.toml`, `Dockerfile`, `docker-compose*`, `*.tf`, `k8s/`/`helm/`, CI files (`.github/workflows`, `.gitlab-ci.yml`),
lint configs (`.editorconfig`, `detekt.yml`, `.eslintrc*`, `ruff.toml`), and an existing `openspec/` folder.

## 2. Fill in CLAUDE.md
Replace every `TODO` in CLAUDE.md with facts from the repo: purpose (from README), stack and versions,
the exact build/test/single-test/lint/run commands (verify each one actually runs), layout, and known gotchas.
Keep CLAUDE.md under ~80 lines. If something cannot be determined, ask the user.

## 3. Prune language rules
In `.claude/rules/lang/`, keep only files for languages present in the repo. Ask before deleting.
For every file you delete, add its path (e.g. `.claude/rules/lang/python.md`) to `.claude/.eng-standards-ignore`
so `/eng:setup` updates do not reinstall it.
Add a new path-scoped rule file if the project uses a language/framework not covered.

## 4. Planning workflow
Ask the user: "Use OpenSpec for this project?"
- Yes and not installed: tell the user to run `npm install -g @fission-ai/openspec@latest` then `openspec init --tools claude`
  (do not install global packages yourself without approval).
- Yes and installed: run `openspec init --tools claude` if `openspec/` does not exist; then put the same stack facts as
  CLAUDE.md in the `context:` of `openspec/config.yaml`.
- Merge the eng rules into `openspec/config.yaml` under `rules:`: take every line from
  `${CLAUDE_PLUGIN_ROOT}/openspec/config-rules.yaml`, replace existing lines starting with `[eng]`, keep the project's
  own rules. Show the diff before writing. These make OpenSpec write measurable scenarios, NFR and Contracts sections,
  and annotated, PR-sized tasks.
- No: the `plan-change` skill is the planning workflow.

## 5. Static analysis (so mechanical issues fail the build, not a review)
Propose, show the diff, and apply after the user agrees — only for the stack detected, reusing existing config:
- Kotlin: detekt (with `buildUponDefaultConfig = true`, `allRules = false`) + ktlint/spotless; Java: Checkstyle or
  Spotless + PMD/ErrorProne. TypeScript: ESLint with typescript-eslint `strict` + Prettier. Python: ruff (`E,F,B,S,UP,SIM`)
  + mypy/pyright.
- Security patterns: a `.semgrep.yml` using registry packs (`p/owasp-top-ten`, `p/secrets`, plus `p/kotlin`,
  `p/java`, `p/typescript` or `p/python` as relevant).
- Wire them into the build/lint command in CLAUDE.md so `/eng:dod` runs them, and make the build fail on errors.

## 6. Reference patterns
Find 3–6 canonical files already in the repo that show how things should be done (a repository with pagination, a
controller with validation, an adapter with timeout/retry, a well-structured test, a migration). Ask the user to
confirm, then list them in CLAUDE.md *Patterns* as `- <what> → path`. New projects: leave the TODO and fill it as the
first good examples get merged.

## 7. Safety net
- Ensure `.gitignore` contains `.env`, `.env.*`, `!.env.example`, `CLAUDE.local.md`, `.claude/settings.local.json`.
- Create `.env.example` with placeholder values if the project uses environment variables.
- Suggest enabling the gitleaks pre-commit hook (`.pre-commit-config.yaml` is included in this template).

## 8. Report
Summarize what was filled in, what was pruned, what needs the user's input.
