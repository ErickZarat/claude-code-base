---
name: bootstrap-project
description: Adapt the eng-standards setup to this repo: fill CLAUDE.md, prune language rules, optional OpenSpec.
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
so `/eng-standards:setup` updates do not reinstall it.
Add a new path-scoped rule file if the project uses a language/framework not covered.

## 4. Planning workflow
Ask the user: "Use OpenSpec for this project?"
- Yes and not installed: tell the user to run `npm install -g @fission-ai/openspec@latest` then `openspec init --tools claude`
  (do not install global packages yourself without approval).
- Yes and installed: run `openspec init --tools claude` if `openspec/` does not exist; then fill `openspec/project.md`
  (or the project context file OpenSpec generated) with the same stack facts as CLAUDE.md.
- No: the `plan-change` skill is the planning workflow.

## 5. Safety net
- Ensure `.gitignore` contains `.env`, `.env.*`, `!.env.example`, `CLAUDE.local.md`, `.claude/settings.local.json`.
- Create `.env.example` with placeholder values if the project uses environment variables.
- Suggest enabling the gitleaks pre-commit hook (`.pre-commit-config.yaml` is included in this template).

## 6. Report
Summarize what was filled in, what was pruned, what needs the user's input.
