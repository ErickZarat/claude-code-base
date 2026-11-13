# Project: <PROJECT_NAME>

<!--
  Keep this file SHORT. It loads into every session.
  Universal rules live in .claude/rules/ (auto-loaded).
  Skills, reviewer agents and the secret guard come from the eng plugin (/plugin).
  Run `/eng:setup` (or the `bootstrap` skill) once to fill in the sections marked TODO.
-->

## What this project is
TODO: one or two sentences — what it does, who uses it.

## Stack
TODO: language + version, framework, database, messaging, build tool.

## Commands (Claude must use these, never guess)
| Purpose      | Command |
|--------------|---------|
| Build        | TODO    |
| Unit tests   | TODO    |
| Single test  | TODO    |
| Lint/format  | TODO    |
| Static analysis | TODO (detekt + Konsist / typescript-eslint strict + knip + dependency-cruiser / ruff + semgrep) |
| Mutation tests (changed files) | TODO (PIT `-DtargetClasses=…` / `stryker run --mutate <files>` / `mutmut run --paths-to-mutate <files>`) |
| Run locally  | TODO    |

## Review
Minimum review depth: standard
<!-- standard (default: every dedicated reviewer) | thorough (same reviewers on opus — auth/payments-heavy code).
     quick (one combined reviewer) is never chosen automatically. -->

## Patterns (copy these — the task plan looks here first)
TODO: `- <what> → path`, e.g. `- paginated repository → src/main/kotlin/.../OrderRepository.kt`

## Layout
TODO: where domain code, adapters, config, tests and migrations live.

## Planning workflow
- If an `openspec/` folder exists: every non-trivial change goes through OpenSpec. Do not code ahead of an approved change:
  `/opsx:propose` → `/eng:spec` (lint + questions) → approve → `/eng:epic` (milestone + one ticket per task) →
  `/eng:task next` per ticket = one tasks.md section (one branch + one PR each, DoD + one review round) → merge →
  `/eng:spec --before-archive` → `/opsx:archive`.
- Bugs and small fixes: `/eng:task <issue>` or `/eng:task new "title" --bug` (lite path, no proposal).
- Team: `/eng:status` shows who is on what, what is blocked and what is ready; `/eng:task next` claims the next ready ticket.
- Decisions: `docs/decisions/` (`decision` skill). Recurring review findings → `/eng:retro` → `.claude/rules/learned.md`.
- Otherwise: use the `plan-change` skill before writing code for anything beyond a one-file fix.

## Non-negotiables (details in .claude/rules/)
1. No vibe coding: understand → plan → small verified steps. Ask when requirements are ambiguous.
2. TDD always: failing test first, then minimum code, then refactor (`tdd` skill).
3. Write the least code that works: reuse the codebase, stdlib and installed dependencies first (ponytail).
4. Depend on interfaces, not implementations (`interface-first-design` skill).
5. Never write, print, log or commit secrets. No backdoors, debug bypasses or hidden flags.
6. A task is done only when `dod` passes. A PR is ready only after one `/eng:review` round: chosen findings fixed and
   confirmed by gates + self-check, every requirement implemented and tested, unfixed blockers listed as pending.

## Project-specific gotchas
TODO: things that are not obvious from the code (generated files, legacy modules, shared libs).
