---
name: plan-change
description: Use before any change larger than a one-file fix in a repo without openspec/: write a short plan and wait for approval.
---

# Plan a change

If the repository has an `openspec/` directory, stop and use the OpenSpec workflow (`/opsx:propose` or the
project's OpenSpec commands) instead of this skill.

## Steps
1. **Understand**: read the relevant code paths end to end. List what you read.
2. **Clarify**: list open questions. If any would change the design, ask them and wait.
3. **Write the plan** (in chat, or in `docs/plans/<yyyy-mm-dd>-<slug>.md` if the user wants it kept):

```markdown
## Goal
One or two sentences. What changes for the user/system.

## Out of scope
What this change deliberately does not do.

## Approach
- Existing code reused/extended (from `reuse-first`):
- New ports/adapters (from `interface-first-design`):
- Data/schema changes and migration strategy:
- Security considerations (auth, input validation, secrets, PII):

## Steps
1. Small, independently verifiable step — files touched — how it is verified.
2. ...

## Tests (written first — TDD)
Behaviours in implementation order, each with its test: unit / integration / edge cases.

## Risks and rollback
```

4. **Wait for approval.** Then implement step by step, verifying each step before the next.
5. If reality diverges from the plan, stop, update the plan, and say what changed and why.
