---
paths:
  - "**/*.kt"
  - "**/*.kts"
  - "**/*.java"
---

# Kotlin / Java (JVM)

- Kotlin: prefer `val`, data classes for values, sealed classes/interfaces for closed result/error hierarchies.
  Avoid `!!`; model absence with nullable types or explicit results. Use `require`/`check` for preconditions.
- Coroutines: structured concurrency only (no `GlobalScope`); inject dispatchers; never block inside coroutines.
- Java: `final` fields, records for immutable data, `Optional` only as return type, never as field/parameter.
- Constructor injection only (Spring: no field `@Autowired`). Beans depend on interfaces.
- Spring Boot: config via `@ConfigurationProperties` + validation; secrets from env/secret manager, never in `application.yml`.
  Controllers stay thin; `@Transactional` at the application-service layer, not on controllers or repositories by default.
- Ktor: install plugins explicitly; validate request bodies; map exceptions with StatusPages to generic client errors.
- gRPC/Protobuf: proto types stay at the edge — map to domain types. Never reuse/renumber field numbers; use `reserved`.
- JDBC/R2DBC/Exposed/jOOQ/JPA: bind parameters only — never Kotlin string templates in SQL (`"... $id"`), including
  `@Query(nativeQuery = true)`, `JdbcTemplate`, `exec(...)`, `DSL.field(String)`. Close resources (`use {}` / try-with-resources).
- Logging: SLF4J with parameterized messages (`log.info("Invoice {} created", invoiceId)`), never string concatenation of secrets.
- Tests: JUnit 5 (+ Kotest/MockK in Kotlin), Testcontainers for real DB/Kafka integration tests.
- Follow ktlint/detekt (Kotlin) or Checkstyle/Spotless (Java) config if present.
