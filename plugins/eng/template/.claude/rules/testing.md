# Testing — TDD is mandatory

## Red → Green → Refactor (follow the `tdd` skill)
- Production code is written ONLY to make a failing test pass. No test first, no code.
- RED: write the smallest test for the next behaviour, run it, and show that it fails for the expected reason
  (an assertion failure, not a compile error or typo).
- GREEN: write the minimum production code to pass it. Run the test again and show it passing.
- REFACTOR: clean up names, duplication and structure with all tests green. No new behaviour during refactor.
- Repeat per behaviour / acceptance scenario. Bug fixes start with a test that reproduces the bug.
- If you wrote production code before its test, delete that code and restart the cycle from RED.
- Exceptions (must be stated explicitly): pure configuration, generated code, spikes the user asked to throw away.

## What good tests look like
- Test behaviour through public interfaces, not private implementation details.
- Name tests as sentences describing behaviour: `returns 404 when invoice does not exist`.
- Arrange / Act / Assert structure; one behaviour per test.
- Every requirement / OpenSpec scenario maps to at least one test, marked with a comment
  `spec: <capability>/<scenario-slug>` (e.g. `// spec: billing/refund-above-total-is-rejected`).
- Unit tests use fakes/stubs of the interfaces (ports) — another payoff of interface-first design.
  Integration tests exercise real adapters (Testcontainers or equivalent) instead of mocking the database.
- Deterministic: no real network, no sleeps, no dependence on wall-clock time or test order. Inject clocks and ID generators.
- Cover edge cases: empty, null/absent, boundaries, invalid input, permission denied, downstream failure/timeout.
- Never delete, skip or weaken a failing test to get green. Fix the code or report the problem.
- Test data uses obviously fake values; never real customer data or real credentials.
