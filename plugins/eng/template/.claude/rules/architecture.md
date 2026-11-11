# Architecture — swappable by design

## Depend on abstractions
- Business logic depends on interfaces (ports), never on concrete infrastructure.
  Databases, HTTP clients, queues, caches, file storage, email/SMS, payment providers, clocks and ID generators
  all sit behind an interface owned by the domain/application layer.
- Concrete implementations (adapters) live in an infrastructure/adapters layer and implement those interfaces.
- Wire implementations through dependency injection (constructor injection). No `new ConcreteThing()` inside business logic,
  no service locators, no static singletons holding state.
- Swapping a provider (e.g. Postgres → ClickHouse, S3 → GCS, Stripe → another PSP) must only require a new adapter
  plus a wiring change — never edits to domain code.

## Interface design
- Name interfaces by capability, from the caller's point of view: `InvoiceRepository`, `PaymentGateway`, `NotificationSender`.
  Implementations name the technology: `PostgresInvoiceRepository`, `StripePaymentGateway`.
- Keep interfaces small and focused (Interface Segregation). Prefer several small ones over one god interface.
- Interfaces use domain types, not vendor SDK types. Do not leak `ResultSet`, SDK clients or HTTP responses through them.
- Do not create an interface for a pure value object or a class that will never have a second implementation
  AND is not an external dependency. Interfaces are for boundaries and variation points, not ceremony.

## Layering
- Dependencies point inward: adapters → application → domain. Domain imports nothing from frameworks.
- Controllers/handlers are thin: validate, map, call a use case, map the result. No business rules there.
- DTOs at the edges, domain models inside. Map explicitly between them.

## API contracts
- .proto, OpenAPI, GraphQL and event schemas are contracts: changes stay backwards compatible (add optional fields,
  never renumber/rename/remove; new endpoint or version for breaking changes).
- A breaking change needs a decision record and `Breaking-change: approved — <reason>` in the PR body
  (the `API contracts` CI check enforces it for .proto and OpenAPI).

## Configuration
- All environment-specific values come from configuration (env vars / config files / secret manager), never hard-coded.
- Configuration is validated at startup; the app fails fast on missing or invalid config.
- Feature switches are explicit, documented configuration — never hidden flags or magic request parameters.
