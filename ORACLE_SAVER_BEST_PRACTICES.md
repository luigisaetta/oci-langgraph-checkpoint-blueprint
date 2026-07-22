# Suggested Best Practices for `OracleSaver`

`OracleSaver` makes LangGraph checkpoints durable by storing them in Oracle Database or Oracle Autonomous Database (ADB). It is a persistence adapter, not a complete workflow-governance layer: applications remain responsible for access control, business-level concurrency, data lifecycle, and the safety of external side effects.

Use this guide when moving from the examples in this repository to a production service.

## At a glance

```text
Request -> authenticated application -> LangGraph graph -> OracleSaver -> Oracle ADB
              |                        |                   |
              |                        |                   +-- durable execution state
              |                        +-- idempotent external side effects
              +-- tenant and thread authorization
```

The database makes state durable. The application defines who may access it, how long it is retained, and how concurrent business actions are resolved.

## Recommended practices

| Area | Recommended practice | Why it matters | Practical guidance |
| --- | --- | --- | --- |
| Connection management | Use a managed `oracledb.ConnectionPool` in production. | A single connection is not safe or sufficient for concurrent HTTP requests and graph runs. | Create one pool during application startup, pass it to `OracleSaver`, and close it at shutdown. Size the pool for service concurrency and the ADB service connection limit. Monitor acquisition wait time and pool exhaustion. |
| Schema migration | Run `OracleSaver.setup()` as a controlled deployment step. | Schema changes need predictable privileges, observability, and failure handling. | Run it once per environment or release using a migration job/account. Do not make ordinary runtime identities permanently responsible for DDL unless that is an intentional operational choice. |
| Thread identifiers | Generate opaque, unique thread IDs and treat them as sensitive references. | A thread ID locates durable workflow state; it is not an authorization boundary. | Generate IDs server-side, associate each with its tenant and owner, and verify that association before every read, resume, or deletion. |
| Authentication and authorization | Enforce authorization in the application layer. | `OracleSaver` persists and retrieves by configuration; it does not implement users, tenants, or permissions. | Require authenticated callers and apply tenant/owner checks before calling `get_state`, resume, list, or delete operations. Do not expose database tables as an application API. |
| Sensitive state | Treat checkpoint state as persisted business data. | Checkpoints can contain prompts, messages, tool inputs, model outputs, and human decisions. | Persist only data needed for recovery. Exclude credentials, access tokens, unnecessary PII, and complete source documents. Apply TLS, database encryption at rest, least-privilege database access, audit logging, and any required redaction or application-level encryption. |
| State size | Keep state small and bounded. | Large values are stored as BLOBs, and long checkpoint histories increase storage and restore cost. | Store durable references to large documents or binary artifacts in a governed object store or domain database when appropriate. Keep only the identifiers and minimal recovery context in graph state. |
| Retention and deletion | Define retention, archive, and purge policies before production use. | `OracleSaver` retains checkpoints, BLOBs, and pending writes until they are explicitly deleted. | Classify threads by lifecycle, purge completed or expired threads with a scheduled job, and test deletion against compliance requirements. Monitor table growth and storage cost. |
| Side effects | Make external operations idempotent. | A recovered graph node can run again; a checkpoint is not an exactly-once delivery guarantee. | Use an idempotency key, transactional outbox, or domain-level operation record for emails, payments, ticket creation, and other irreversible actions. Keep code before `interrupt()` deterministic and free of non-idempotent effects. |
| Concurrent resume | Serialize or arbitrate business actions for the same thread. | The saver does not choose between two simultaneous resumes or conflicting approvals. | Use a distributed lock, optimistic version check, or a single-threaded work queue keyed by `thread_id`. Define an explicit conflict response and audit trail. |
| Reliability | Add retries, timeouts, and health checks around database access. | The saver surfaces driver and database errors; it does not provide service-level resilience policy. | Configure sensible pool acquisition and request timeouts. Retry only transient, safe operations with bounded backoff. Expose readiness that validates a borrowed connection, and emit metrics for database errors and latency. |
| Observability | Measure checkpoint behaviour as part of the workflow service. | Durable state failures and unbounded growth are difficult to diagnose from application logs alone. | Track checkpoint read/write latency, error rates, pool wait time, active paused threads, resume failures, checkpoint size, and row/BLOB growth by tenant and workflow type. Avoid logging checkpoint payloads containing sensitive data. |
| Dependency management | Pin and test the LangGraph, Oracle saver, and Oracle driver versions together. | Checkpoint formats and APIs evolve across package releases. | Maintain a constraints or lock file. Before an upgrade, test new writes, restore of existing checkpoints, interrupted-run resume, and schema setup in a representative ADB environment. |
| Production validation | Run integration and recovery tests against a real Oracle target. | Mock unit tests cannot validate Oracle JSON, BLOB handling, connection recovery, DDL, or contention. | Test process restart at each graph boundary, lost connections, large state values, schema upgrades, retention jobs, and concurrent resume attempts. Use production-like database settings and payload sizes. |

## Deployment checklist

Before enabling a checkpointed graph for production traffic, confirm that:

- A managed connection pool, readiness check, timeouts, and monitoring are in place.
- `OracleSaver.setup()` has run successfully through the deployment process.
- Thread ownership and tenant authorization are enforced by the application.
- The checkpoint state has been reviewed for confidential and regulated data.
- Retention, purge, backup, and recovery responsibilities have named owners.
- External side effects are idempotent and concurrent resume behaviour has an explicit policy.
- The exact dependency set and a real-ADB recovery test have been recorded for the release.

## Scope of the examples

The examples in this repository demonstrate durable state, human-in-the-loop interruption and resume, and a pooled service lifecycle. They intentionally do not provide a full production implementation of authentication, tenant isolation, retention automation, distributed locking, or exactly-once side-effect processing. Those controls should be designed around `OracleSaver` for the business domain being deployed.
