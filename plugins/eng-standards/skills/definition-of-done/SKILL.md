---
name: definition-of-done
description: Use before saying a coding task is done, committing, or opening a PR: build, tests, lint, diff and security checks, honest summary.
---

# Definition of done

A task is NOT done until every item below passes or is explicitly reported as failing.

## 1. Verify (use the commands in CLAUDE.md — never guess)
- [ ] Build/compile succeeds.
- [ ] Tests pass — run the relevant tests, then the full suite if it is reasonably fast.
- [ ] Linter/formatter/type-checker clean for changed files.
Paste the real result (pass/fail counts or the error), not "should work".

## 2. Review the diff (`git diff`, `git status`)
- [ ] Only files related to the task changed. No stray debug code, `println`/`console.log`, commented-out code, or TODO stubs.
- [ ] No duplicated logic — `reuse-first` decisions were applied.
- [ ] External dependencies sit behind interfaces — `interface-first-design` applied where relevant.
- [ ] Names are descriptive; comments explain why; public APIs have doc comments.
- [ ] Errors handled with context; inputs validated at boundaries; no swallowed exceptions.
- [ ] TDD was followed: every new behaviour has a test that was seen failing before the code existed.
- [ ] Tests cover the new behaviour and its edge cases; no tests were skipped, deleted or weakened.
- [ ] Every requirement / OpenSpec scenario / plan step is implemented (for features, run the `requirements-verifier` agent).
- [ ] Docs/README/`.env.example`/OpenSpec specs updated if behaviour or configuration changed.

## 3. Security
- [ ] Run the `secure-self-review` skill and fix HIGH/CRITICAL findings.

## 4. Summary to the user
```
Done: <one line>
Changed: <files / modules>
Verified: <build/test/lint results>
Security: <scan results or "tools not installed — manual review only">
Follow-ups / risks: <or "none">
```
If anything failed or could not be verified, say so plainly at the top instead of reporting success.
