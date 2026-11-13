# Code quality

## Naming
- Names say WHAT something is or does, in plain domain language: `calculateMonthlyInvoiceTotal`, not `calc` or `doStuff`.
- Booleans read as questions: `isExpired`, `hasPermission`, `shouldRetry`.
- Functions are verbs, types are nouns. No abbreviations except universally known ones (`id`, `url`, `http`).
- No single-letter names outside short lambdas and loop indices. No `data`, `info`, `temp`, `obj`, `manager`, `helper`, `utils`
  as the whole name — say what it holds or does.
- Follow the naming conventions of the language and of the existing codebase.

## Comments (the "why, not how" rule comes from ponytail)
- Write comments for a teammate reading the code in a year: plain language, links to specs/tickets where useful.
- A comment, README or PR line claims only what the code or a test shows ("exact", "never", "safe" need a test).
- Public APIs (interfaces, public classes/functions, endpoints) get doc comments: purpose, parameters, return, errors thrown.
- Do not narrate obvious code (`// increment i`). Do not leave AI chatter ("Here is the updated function…").
- Keep comments true: update or delete them when the code changes.

## Structure
- Functions do one thing. If you need "and" to describe it, split it. Aim for < ~30 lines.
- Prefer early returns over deep nesting (max ~3 levels).
- No magic numbers or strings — named constants or configuration.
- Prefer immutability and pure functions; isolate side effects (I/O, time, randomness) at the edges.
- Keep files cohesive; one main type per file unless the language idiom says otherwise.

## DRY (searching before writing and no premature abstraction come from ponytail)
- Duplicate logic (even "slightly different") is extracted into one shared, well-named unit.

## Errors and logging
- Never swallow exceptions. Handle them where you can act; otherwise propagate with context.
- Use specific error types; error messages say what failed and with which (non-sensitive) identifiers.
- Validate inputs at boundaries (API, messaging, file, CLI) and fail fast with clear messages.
- Structured logging at the right level (debug/info/warn/error). Never log secrets, tokens, passwords or full PII.
- No `println`/`console.log`/`print` debugging left in committed code.

## Efficiency
- Choose the right data structure first; avoid N+1 queries, unbounded loops over remote calls, and loading whole tables into memory.
- Paginate or stream large results. Set timeouts on every network call.
- Do not micro-optimise without a measurement; do not ignore obvious algorithmic waste either.
