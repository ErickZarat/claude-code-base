---
name: tdd
description: Use before writing any production code for a feature, change or bug fix: red → green → refactor with real test output.
---

# Test-driven development

## 0. List the behaviours
From the requirement (OpenSpec scenario, plan step, issue), write a short list of behaviours to implement,
including edge cases and failure paths. Each becomes one cycle. Order them simplest first.

## 1. RED — one failing test
- Write ONE test for the next behaviour, using the public interface (or the port it should go behind).
- Production types it needs may be created as empty stubs so it compiles; no logic yet.
- Run only that test. Paste the result. It must fail on the assertion, for the reason you expect.
  - Passes already? The behaviour exists or the test is wrong — investigate before continuing.
  - Fails for another reason (compile error, setup error)? Fix the test setup and rerun until it is a genuine RED.

## 2. GREEN — minimum code
- Write the simplest production code that makes the test pass. No extra features, no speculative parameters.
- Run the test, then the related test class/module. Paste the result. All green before moving on.

## 3. REFACTOR — with a green safety net
- Remove duplication, improve names, extract to existing shared code (`reuse-first`), put external calls behind ports
  (`interface-first-design`).
- Run the tests again. Still green. Behaviour unchanged.

## 4. Repeat
Next behaviour from the list. Commit at green points if the user wants small commits
(e.g. `test: ...` + `feat: ...`, or one commit per cycle).

## Rules
- Never write production logic before a failing test exists for it. If it happened, delete that code and go back to RED.
- Never edit a test to make it pass unless the test itself was wrong — and say so when you do.
- Keep a running checklist of behaviours: done / in progress / remaining. Show it at the end.
