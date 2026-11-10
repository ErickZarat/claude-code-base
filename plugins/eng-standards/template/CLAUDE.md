# Project: <PROJECT_NAME>

<!--
  Keep this file SHORT. It loads into every session.
  Universal rules live in .claude/rules/ (auto-loaded).
  Skills, reviewer agents and the secret guard come from the eng-standards plugin (/plugin).
  Run `/eng-standards:setup` (or the `bootstrap-project` skill) once to fill in the sections marked TODO.
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
| Run locally  | TODO    |

## Layout
TODO: where domain code, adapters, config, tests and migrations live.

## Planning workflow
- If an `openspec/` folder exists: every non-trivial change goes through OpenSpec
  (propose → review → apply → archive). Do not code ahead of an approved change.
- Otherwise: use the `plan-change` skill before writing code for anything beyond a one-file fix.

## Non-negotiables (details in .claude/rules/)
1. No vibe coding: understand → plan → small verified steps. Ask when requirements are ambiguous.
2. TDD always: failing test first, then minimum code, then refactor (`tdd` skill).
3. Reuse before you write: search the codebase first (`reuse-first` skill).
4. Depend on interfaces, not implementations (`interface-first-design` skill).
5. Never write, print, log or commit secrets. No backdoors, debug bypasses or hidden flags.
6. A task is done only when `definition-of-done` passes. Changes are merge-ready only after `/eng-standards:review-cycle`
   (review → fix → re-review rounds) exits clean: no open blockers, every requirement implemented and tested.

## Project-specific gotchas
TODO: things that are not obvious from the code (generated files, legacy modules, shared libs).
