# Self-check — the same checklist the reviewers use, applied by the author before the PR

Walk the diff once, top to bottom. Fix what you find; don't report it. Skip lines that don't apply to the change.
(`tests/test_review_coverage.py` keeps this list in sync with every reviewer's checklist.)

## Requirements
- Every requirement / acceptance criterion maps requirement → code → test; nothing missing, nothing extra (no scope creep).
- Tests for OpenSpec scenarios carry `spec: <capability>/<scenario>`; `trace.py --change <change>` shows none untested.
- Non-functional requirements (design.md/proposal.md) are met — latency, volume, security, observability targets.
- TDD: each test was seen failing first; commit history shows tests with or before the code they cover.

## Security
- No hard-coded secrets, tokens or credentialed URLs (tests, docs, comments too); no secrets or PII in logs or errors.
- No backdoor, debug endpoint, default password or auth bypass; TLS verification, CSRF and auth stay on; no CORS `*` with credentials.
- Input validated at every boundary — unvalidated input is a bug; no shell/NoSQL/template injection, path traversal, unsafe deserialization.
- SQL injection: values only as bound parameters — never string templates (`"$id"`, `"${x}"`), concatenation, f-strings,
  `%`/`format`; ORDER BY / column / table names from an allowlist; LIKE wildcards escaped; native queries (JPA native,
  JdbcTemplate, jOOQ `DSL.field(String)`, Exposed `exec`, MyBatis `${}`) and stored procedures checked too. Read the
  packet's "Dynamic SQL candidates" (`review_packet.py`) — it must be empty or every line justified.
- Server-side authorization per resource (no IDOR); a generic error response to clients, details only in server logs.
- Password hashing with Argon2id/bcrypt/scrypt; no home-made crypto.
- New dependencies justified and pinned; no unexpected outbound calls or telemetry; new config keys in `.env.example`.
- API contracts (.proto/OpenAPI/events) stay backwards compatible, or are versioned with a decision record.

## Tests
- No new behaviour without tests; edge and failure cases covered (empty, invalid, not found, limits, downstream failure).
- No weakened, skipped or deleted tests; no non-deterministic tests (time, network, order — inject clocks).

## Correctness
- No swallowed exceptions or silent failure; errors carry context; retries and timeouts bounded.
- Null/empty/boundary handling; no race condition on shared state.

## Design
- Infrastructure behind an interface (port); no vendor types leaking through it; no business logic in controllers/adapters.
- No duplicated logic — reused existing code (codebase → stdlib → installed dependency) and followed the project's reference patterns (CLAUDE.md).
- Type design: invariants enforced by types/constructors, encapsulation (no public mutable state); no needless complexity — simplify.

## Readability
- Descriptive names; comments explain *why*; no stale or inaccurate comment left; doc comments on public APIs.
- No leftover debug code, TODOs or commented-out code.

## Efficiency
- No N+1 queries or lazy loads in loops, no remote calls in loops (batch); queries paginated or limited.
- Every network call has a timeout; no blocking calls on coroutine/event-loop threads.
