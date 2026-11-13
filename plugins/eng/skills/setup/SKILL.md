---
name: setup
description: Install or update the eng rules, CLAUDE.md, settings and pre-commit in this project.
disable-model-invocation: true
argument-hint: "[--dry-run] [--user]"
---

# Set up eng in this project

1. Locate the installer: `${CLAUDE_PLUGIN_ROOT}/install.sh`.
   If that path does not exist (variable not expanded), find it with
   `find ~/.claude/plugins -path '*claude-code-base/eng/*/install.sh' | head -1`.
2. Show the user what will happen first: run `bash <installer> --dry-run $ARGUMENTS "$PWD"` and summarise the output.
3. Run it for real: `bash <installer> $ARGUMENTS "$PWD"`.
4. If the output lists **locally modified** files, for each one show the diff between `<file>` and `<file>.eng-new`,
   propose a merge, apply it once the user agrees, then delete the `.eng-new` file.
5. If `CLAUDE.md` was just created (first install), follow `${CLAUDE_PLUGIN_ROOT}/skills/bootstrap/SKILL.md` to fill it in.
6. If `openspec/config.yaml` exists, compare its `[eng]` rules with `${CLAUDE_PLUGIN_ROOT}/openspec/config-rules.yaml`;
   if they differ or are missing, show the diff and offer to merge (same procedure as the bootstrap skill).
7. Static analysis and mutation profile for the detected stack — propose, install only what the user accepts, and
   fill the CLAUDE.md *Static analysis* and *Mutation tests* rows:
   - **Kotlin/JVM:** detekt + ktlint (strict), Konsist (or ArchUnit) tests for the architecture rules (domain imports
     no framework/infrastructure, adapters implement ports), PIT for mutation tests.
   - **TypeScript:** typescript-eslint `strict-type-checked`, `knip` (unused code/deps), `dependency-cruiser` (layer
     rules), Stryker for mutation tests.
   - **Python:** ruff (with `B`, `S`, `SIM`), import-linter, mutmut.
   Plus `semgrep` with the project's rules (SQL string building, secrets in logs) for every stack.
8. Companion plugins: if `.claude/settings.json` already existed, make sure it registers the `ponytail`
   (`DietrichGebert/ponytail`) and `cursor-plugins` (`cursor/plugins`) marketplaces and enables `ponytail@ponytail` and
   `pstack@cursor-plugins` like `${CLAUDE_PLUGIN_ROOT}/template/.claude/settings.json`; show the diff and add them once the
   user agrees. ponytail's hooks need `node` on PATH — warn if `command -v node` fails.
9. Remind the user to commit `.claude/`, `CLAUDE.md`, `.pre-commit-config.yaml` and `.gitignore` so teammates get the same setup.
