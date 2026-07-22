# Example 03: Production-Oriented HITL Recovery with ADB Pooling

Example 03 evolves Example 02 into an operational durability demonstration. FastAPI owns an Oracle ADB connection pool for its lifecycle, while LangGraph checkpoints retain the workflow state outside the server process. You can stop the server while an approval is pending, start a new server process, inspect the same thread, and resume it.

The workflow remains deterministic: `IntakeNode` normalizes a message, `DraftNode` creates a draft, and `ApprovalNode` pauses with `interrupt()`. This keeps the focus on operational recovery rather than on LLM variability.

For a concise, action-and-observation walkthrough of the restart scenario, use the dedicated [Recovery Demonstration Runbook](RECOVERY_DEMO.md).

## What changes from Example 02

| Concern | Example 02 | Example 03 |
| --- | --- | --- |
| Database access | Opens a connection for each stream. | Creates one `oracledb.ConnectionPool` during FastAPI startup. |
| Client interaction | One interactive process starts and resumes a run. | Separate `start`, `status`, and `decide` commands. |
| Restart demonstration | Resume is shown in one running server process. | A paused thread is inspected and resumed after a server restart. |
| Repeated decision | Not handled separately. | A matching final decision is acknowledged idempotently. |

## Prerequisites and configuration

Complete the repository [Quick Start](../../QUICKSTART.md). The ADB schema owner must be able to create the OracleSaver tables and indexes on the first startup.

Copy `.env.sample` to `.env` if needed, then configure the normal ADB wallet variables and these Example 03 values:

| Variable | Required | Purpose | Safe example |
| --- | --- | --- | --- |
| `EXAMPLE03_SERVER_PORT` | No | Local port used by this example. | `8081` |
| `DB_POOL_MIN` | Yes | Connections created at startup. | `2` |
| `DB_POOL_MAX` | Yes | Maximum ADB connections used by this server process. | `10` |
| `DB_POOL_INCREMENT` | Yes | Connections added when the pool grows. | `1` |
| `NEXTJS_UI_ORIGIN` | No | Exact Next.js browser origin permitted by CORS for Example 04. | `http://127.0.0.1:3000` |

All pool values must be positive integers, and `DB_POOL_MIN` must not be greater than `DB_POOL_MAX`. Size the maximum according to expected concurrent load and the connection limit of the target ADB service; the example values are for local demonstration only.

For the browser UI demonstration, `NEXTJS_UI_ORIGIN` must be a bare `http` or `https` origin with no path. Example 03 allows that one origin through CORS and does not enable credentialed cross-origin requests. See [Example 04](../example04_nextjs_ui/README.md) for the Next.js client.

## Start the server

From the repository root:

```bash
conda activate oci-langgraph-checkpoint-blueprint
./examples/example03_production_hitl/start_server.sh
```

During FastAPI startup, the application creates one pool, passes it to `OracleSaver`, and runs `OracleSaver.setup()` once. It closes the pool on shutdown.

Check pool and database readiness from a second terminal:

```bash
curl http://127.0.0.1:8081/health/ready
```

Expected response:

```json
{"status":"ready"}
```

## Operational restart demonstration

Use three independent client actions. The client calls only the HTTP API and never reads ADB credentials, so every command can run in a separate terminal or later session.

### 1. Start a run and record its durable thread ID

```bash
python -m examples.example03_production_hitl.client start \
  "Prepare the quarterly report"
```

The client displays SSE events until `approval_required`, then exits. Record the printed ID:

```text
Workflow paused and persisted in ADB.
Thread ID: example03-<generated-id>
```

At this point the latest checkpoint has `status` equal to `awaiting_approval`; no decision has been supplied.

### 2. Restart the FastAPI service

In the terminal running the server, stop it with `Ctrl-C`. Start it again with the same command:

```bash
./examples/example03_production_hitl/start_server.sh
```

This simulates a process restart or a replacement instance during a deployment. The new process creates a new pool, but it connects to the same ADB schema containing the existing LangGraph checkpoints.

### 3. Inspect the paused thread after restart

Replace `<thread-id>` with the ID from step 1:

```bash
python -m examples.example03_production_hitl.client status <thread-id>
```

Observe a response shaped like:

```json
{
  "thread_id": "example03-<generated-id>",
  "status": "awaiting_approval",
  "draft": "Proposed response: Prepare the quarterly report",
  "approval_decision": null,
  "approval_required": true
}
```

This proves the new server process loaded state from ADB rather than from the memory of the stopped process.

### 4. Resume the persisted thread

```bash
python -m examples.example03_production_hitl.client decide <thread-id> approve
```

The client streams the final approval node update and `run_completed`. It uses `POST /runs/{thread_id}/decision`; the server invokes `Command(resume="approve")` with the same `thread_id`.

### 5. Verify the final state

```bash
python -m examples.example03_production_hitl.client status <thread-id>
```

Observe `status: "approved"`, `approval_decision: "approve"`, and `approval_required: false`. Repeat the `decide` command with `approve` to receive an idempotent `run_completed` event without a second graph execution. Sending `reject` after approval returns HTTP `409 Conflict`.

## API contract

| Endpoint | Purpose |
| --- | --- |
| `GET /health/ready` | Acquires a pool connection and runs `SELECT 1 FROM dual`. |
| `POST /runs` | Starts an `example03-` thread and returns an SSE stream. |
| `GET /runs/{thread_id}` | Returns the current state reconstructed from ADB checkpoints. |
| `POST /runs/{thread_id}/decision` | Resumes a paused run, or returns an idempotent completion stream for a matching terminal decision. |

The idempotency behaviour covers repeated decisions sent after a completed state has been persisted. Coordinating simultaneous, conflicting decisions from separate clients requires a business-level concurrency policy or distributed lock and is intentionally outside this example.

## Inspect the persisted checkpoints in ADB

Use the same read-only query pattern as Example 02, replacing the prefix:

```sql
SELECT
    thread_id,
    checkpoint_ns,
    checkpoint_id,
    parent_checkpoint_id,
    JSON_SERIALIZE(metadata RETURNING VARCHAR2(4000)) AS metadata_json
FROM checkpoints
WHERE thread_id LIKE 'example03-%'
ORDER BY thread_id, checkpoint_id;
```

Run it after step 1 and again after step 4. The pause checkpoint remains in the history, and later checkpoints record the final approval result.

## Implementation map

| Concern | File |
| --- | --- |
| Pool configuration and creation | [pool.py](pool.py) |
| FastAPI lifecycle, status, readiness, and idempotent decision API | [app.py](app.py) |
| Three-command recovery client | [client.py](client.py) |
| Shared deterministic graph and HITL node | [Example 02 graph](../example02_hitl_sse/graph.py) and [approval node](../example02_hitl_sse/nodes/approval.py) |
