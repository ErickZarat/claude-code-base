---
name: setup
description: Installs or updates the eng-standards project files (rules, CLAUDE.md, settings, pre-commit) in the current repository, then hands over to bootstrap-project for new installs. Use when the user asks to set up, add, or update the engineering standards / base Claude setup in a project.
disable-model-invocation: true
argument-hint: "[--dry-run] [--user]"
---

# Set up eng-standards in this project

1. Locate the installer: `${CLAUDE_PLUGIN_ROOT}/install.sh`.
   If that path does not exist (variable not expanded), find it with
   `find ~/.claude/plugins -path '*eng-standards*/install.sh' | head -1`.
2. Show the user what will happen first: run `bash <installer> --dry-run $ARGUMENTS "$PWD"` and summarise the output.
3. Run it for real: `bash <installer> $ARGUMENTS "$PWD"`.
4. If the output lists **locally modified** files, for each one show the diff between `<file>` and `<file>.eng-new`,
   propose a merge, apply it once the user agrees, then delete the `.eng-new` file.
5. If `CLAUDE.md` was just created (first install), run the `bootstrap-project` skill to fill it in.
6. Remind the user to commit `.claude/`, `CLAUDE.md`, `.pre-commit-config.yaml` and `.gitignore` so teammates get the same setup.
