---
name: interface-first-design
description: Use when adding or changing anything external or replaceable (DB, cache, queue, API, storage, payments, clock): port + adapter + DI.
---

# Interface-first design (ports and adapters)

## Steps
1. **Identify the capability** the business code needs, in domain terms — not the technology.
   "Store and fetch invoices", not "talk to Postgres".
2. **Check for an existing port** (search the codebase first). Extend it only if the new methods belong to the same capability.
3. **Define the port** in the domain/application layer:
   - Name = capability (`InvoiceRepository`, `PaymentGateway`, `FileStorage`, `Clock`).
   - Methods use domain types only. No vendor SDK types, no transport details, no framework annotations.
   - Errors are expressed as domain errors / sealed results, not vendor exceptions.
   - Keep it minimal: only the methods current use cases need.
   - Doc comment: what the capability guarantees (ordering, idempotency, consistency, timeouts).
4. **Implement the adapter** in the infrastructure layer:
   - Name = technology + port (`PostgresInvoiceRepository`, `S3FileStorage`).
   - Translate vendor types and exceptions to domain ones at this boundary.
   - All connection details/credentials come from injected configuration.
5. **Wire via dependency injection** (constructor injection; selection by configuration/profile if multiple adapters exist).
6. **Test both sides**:
   - Use-case tests with an in-memory fake of the port.
   - Adapter integration test against the real technology (Testcontainers or equivalent).
   - Optional: a shared contract test suite every adapter must pass — guarantees swappability.

## Do not
- Create interfaces for value objects or internal helpers with a single, non-external implementation.
- Mirror a vendor API 1:1 as the "interface" — that just moves the coupling.
- Let adapters contain business rules.

## Output
State the port signature, adapter name, wiring location and test plan before writing the code.
