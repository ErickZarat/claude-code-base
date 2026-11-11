# Security — non-negotiable

## Secrets
- Never hard-code passwords, API keys, tokens, private keys, connection strings with credentials, or signing secrets.
  Read them from environment variables or a secret manager.
- Never read, print, echo, log or paste the contents of `.env`, key files or credential stores.
  Use `.env.example` with placeholder values to document required variables.
- Never put secrets in test fixtures, logs, error messages, URLs, comments, commit messages or documentation.
- If you notice an existing committed secret, stop and tell the user. Do not "fix" it silently — it must be rotated.

## No backdoors
- No hidden admin users, default passwords, master keys, magic headers/parameters, debug endpoints,
  or "temporary" auth bypasses — not even behind a flag, not even "for testing".
- No code that disables TLS verification, CSRF protection, auth checks or input validation.
- No outbound calls to endpoints the user has not asked for. No telemetry added silently.
- Never obfuscate code or add behaviour that is not described in the change summary.

## Input and output
- Treat all external input as untrusted: validate type, length, format and range at the boundary.
- SQL: bound parameters / ORM bindings only. Never splice values into SQL via concatenation, string templates
  (`"$id"`, `"${x}"`), f-strings or format functions — native queries included. Identifiers that can't be bound
  (ORDER BY, column/table names) come from an allowlist. Escape LIKE wildcards from input.
- Shell/OS commands: avoid; if unavoidable, pass arguments as arrays, never interpolate user input.
- Output encoding for HTML/JS contexts; no `innerHTML`/`eval`/`dangerouslySetInnerHTML` with untrusted data.
- File paths from users are normalized and confined to an allowed directory (no path traversal).
- Deserialization only of trusted formats into explicit types; no polymorphic/native deserialization of untrusted data.

## AuthN / AuthZ
- Authorization is checked server-side on every request, for every resource (no IDOR).
- Passwords: hashed with a slow adaptive algorithm (Argon2id/bcrypt/scrypt). Never encrypted, never MD5/SHA-1.
- Use well-known libraries for crypto, JWT and OAuth. Never roll your own crypto.
- Least privilege for service accounts, DB users, IAM roles and tokens.

## Dependencies
- Prefer the standard library and already-used dependencies. New dependencies must be well-maintained and justified.
- Pin versions via lock files. Never add a package you cannot verify exists (watch for typo-squatting / hallucinated names).

## Data
- Minimise PII collected and logged. Mask identifiers in logs.
- Error responses to clients are generic; details go to server logs (without secrets).
