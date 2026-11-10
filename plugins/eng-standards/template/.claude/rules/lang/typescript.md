---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
  - "**/*.mjs"
---

# TypeScript / JavaScript

- `strict` TypeScript. No `any` (use `unknown` + narrowing), no non-null `!` assertions to silence the compiler.
- Prefer `const`, `readonly`, discriminated unions for states/results; avoid enums in favour of union literals unless the codebase uses them.
- Validate all external data at runtime (zod/valibot or the project's validator) — types alone do not validate input.
- Async: always `await` or explicitly handle promises; no floating promises; set timeouts/AbortSignal on fetch.
- Frontend: never put secrets in client bundles (anything `NEXT_PUBLIC_`/`VITE_` is public). No `dangerouslySetInnerHTML`/`innerHTML` with untrusted data.
- Server: parameterized queries via the ORM/query builder; helmet/CORS configured explicitly; no wildcard CORS with credentials.
- Use the project's formatter/linter (ESLint, Prettier/Biome). Do not disable rules inline without a comment explaining why.
