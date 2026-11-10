---
paths:
  - "**/*.sql"
  - "**/migrations/**"
  - "**/db/migration/**"
  - "**/changelog/**"
---

# SQL and migrations

- Never edit a migration that has already been applied/merged. Create a new one.
- Migrations are forward-only, idempotent where the tool allows, and safe for zero-downtime deploys
  (add nullable column → backfill → add constraint; no long table locks on large tables).
- Every new foreign key and frequent filter column gets an index decision (documented if skipped).
- No credentials, environment-specific hostnames or real data in migrations or seed files.
- Name constraints and indexes explicitly and consistently.
- ClickHouse/TimescaleDB: choose ORDER BY / partition / chunk keys deliberately and document the reasoning.
