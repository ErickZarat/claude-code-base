---
name: secure-self-review
description: Use after writing or changing code that touches input handling, auth, data access, config, secrets, file/OS access, networking or dependencies — and always as part of definition-of-done. Reviews the diff for leaked secrets, backdoors and common vulnerabilities.
---

# Secure self-review

Review the actual diff (`git diff` and `git diff --staged`, plus untracked files), not your memory of it.

## 1. Automated scans (run what is available, report results)
- Secrets: `gitleaks detect --no-banner --redact --source .` or `gitleaks protect --staged --redact`
  (fallback: `trufflehog filesystem . --only-verified` if installed).
- Dependencies: the ecosystem's audit (`./gradlew dependencyCheckAnalyze`, `npm audit --omit=dev`, `pip-audit`, `osv-scanner -r .`) if configured.
- SAST: `semgrep scan --config auto --error` if installed.
If a tool is not installed, say so and continue with the manual checklist. Never install tools globally without asking.

## 2. Manual checklist (answer each against the diff)
- [ ] No hard-coded secrets, tokens, passwords, private keys or credentialed URLs — including in tests, docs, comments.
- [ ] No reads/prints/logs of `.env` or secret values. New config keys documented in `.env.example` with placeholders.
- [ ] No backdoors: hidden users, default passwords, magic headers/params, debug/admin endpoints, auth bypass flags.
- [ ] No disabled security controls (TLS verification, CSRF, CORS `*` with credentials, auth middleware).
- [ ] All external input validated at the boundary; SQL parameterized; no shell interpolation; no unsafe deserialization.
- [ ] Authorization checked per resource on the server side.
- [ ] Errors to clients are generic; logs contain no secrets or full PII.
- [ ] New dependencies exist, are maintained, pinned, and justified.
- [ ] No unexpected outbound network calls or telemetry.

## 3. Report
List each finding as `severity — file:line — issue — fix`. Fix HIGH/CRITICAL before declaring done.
If a real secret was already committed, tell the user it must be rotated (rewriting history alone is not enough).
