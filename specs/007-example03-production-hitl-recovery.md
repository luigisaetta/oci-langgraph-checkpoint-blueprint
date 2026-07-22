# Specification: Example 03 — Production-Oriented HITL Recovery with ADB Pooling

## Status

Accepted

## Context

Example 02 proves that a Human-in-the-Loop (HITL) LangGraph workflow can pause and resume through checkpoints stored in Oracle Autonomous Database (ADB). A production HTTP service also needs to reuse database sessions efficiently and prove that a persisted approval request can survive a FastAPI process restart.

## Scope

Create `examples/example03_production_hitl/`, a production-oriented evolution of Example 02. It must use an Oracle connection pool managed by the FastAPI lifecycle, expose a durable-run status endpoint, and provide a non-interactive CLI that demonstrates start, restart, inspection, and resume as independent operations.

## Connection Pool Contract

1. The FastAPI lifespan must create one wallet-based `oracledb.ConnectionPool` when the application starts and close it during shutdown.
2. The pool must be passed directly to `OracleSaver`; `OracleSaver.setup()` must run once during application startup before requests are served.
3. Pool settings must be loaded from the repository-root `.env` file through `DB_POOL_MIN`, `DB_POOL_MAX`, and `DB_POOL_INCREMENT`. They must be validated as positive integers, with `DB_POOL_MIN <= DB_POOL_MAX`.
4. The example must use `EXAMPLE03_SERVER_PORT`, defaulting to `8081`, so it can run alongside Example 02.

## Durable Recovery Contract

1. `POST /runs` must start a new `example03-` thread and stream updates until it pauses for approval.
2. `GET /runs/{thread_id}` must retrieve the persisted graph state from ADB and return the thread ID, lifecycle status, draft, approval decision, and whether an approval decision is still required. It must return `404` for an unknown thread.
3. `POST /runs/{thread_id}/decision` must resume an `awaiting_approval` thread using `Command(resume=...)` and stream the result.
4. A repeated decision matching the already persisted final decision must return a `run_completed` SSE event without invoking the graph again. A conflicting decision, an unknown thread, or a thread that is not awaiting approval must return an actionable HTTP error.
5. The example must document that duplicate-decision handling is sequential idempotency; multi-writer decision arbitration is outside this example's scope.
6. `GET /health/ready` must confirm that a pool connection can be acquired and used for a validation query.

## Client Contract

1. Provide a Python client with three subcommands:
   * `start <message>` starts a workflow, displays the pause data and thread ID, then exits without submitting a decision.
   * `status <thread_id>` displays the state returned by `GET /runs/{thread_id}`.
   * `decide <thread_id> <approve|reject>` streams the resume operation to completion.
2. The client must use only the HTTP API; it must not require ADB credentials or retain workflow state in process memory between commands.
3. The `start` output must tell the user how to simulate a server restart and which `status` command to run next.

## Documentation and Testing

1. The example README must link to a dedicated `RECOVERY_DEMO.md` runbook. The runbook must provide an operational, step-by-step restart demonstration with a clear "What you do" and "What you observe" section for each stage: start a run, record its thread ID, stop and restart the server, inspect the persisted state, resume it, verify its completed state, and demonstrate sequential idempotency.
2. The README must document pool configuration, API endpoints, idempotency behaviour, and the distinction between this example's deterministic workflow and production deployment policy.
3. Unit tests must cover pool configuration validation, status retrieval response handling, unknown-run handling, sequential idempotent decisions, conflicting decisions, and CLI argument parsing without a live ADB or OCI resource.
4. The main README and `CHANGELOG.md` must link to and record Example 03.

## Acceptance Criteria

* The server owns exactly one connection pool for its lifespan and initializes the checkpoint schema once.
* The same `example03-` thread can be inspected and resumed after a fresh application instance is created against the same ADB schema.
* A duplicate completed decision produces an idempotent `run_completed` event and does not invoke the graph streamer.
* The client supports the documented `start`, `status`, and `decide` commands.
* `RECOVERY_DEMO.md` enables a user to perform and observe the complete restart recovery scenario without inferring intermediate actions.
* Tests run without a live OCI or ADB connection.

## Out of Scope

* A real LLM provider, tools, or non-deterministic agent behaviour.
* OCI deployment manifests, load balancers, authentication, and authorisation.
* Distributed locking or simultaneous conflicting approvals from multiple clients.
