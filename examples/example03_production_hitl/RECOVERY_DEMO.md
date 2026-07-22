# Example 03 Recovery Demonstration Runbook

Use this runbook to demonstrate that a Human-in-the-Loop workflow paused in LangGraph can survive a FastAPI server restart because its checkpoints are stored in Oracle Autonomous Database (ADB).

The only value you must keep between steps is the `thread_id` printed by the client. Neither the original FastAPI process nor the original client process needs to remain running.

## Before you start

### What you do

1. Complete the repository [Quick Start](../../QUICKSTART.md).
2. Configure the ADB wallet and database variables in the repository-root `.env` file.
3. Add the Example 03 pool settings if they are not already present:

   ```dotenv
   EXAMPLE03_SERVER_PORT=8081
   DB_POOL_MIN=2
   DB_POOL_MAX=10
   DB_POOL_INCREMENT=1
   ```

4. Activate the project environment:

   ```bash
   conda activate oci-langgraph-checkpoint-blueprint
   ```

### What you observe

The configuration contains no credentials in commands or source code. The configured ADB schema owner has permission to create the checkpoint tables and indexes on its first use.

## Step 1: Start the server

### What you do

In terminal A, from the repository root, run:

```bash
./examples/example03_production_hitl/start_server.sh
```

Wait until Uvicorn reports that the application startup is complete.

In terminal B, verify readiness:

```bash
curl http://127.0.0.1:8081/health/ready
```

### What you observe

The readiness command returns:

```json
{"status":"ready"}
```

This means FastAPI created its ADB connection pool and successfully borrowed a connection to run `SELECT 1 FROM dual`. During startup, `OracleSaver.setup()` also created or upgraded the checkpoint schema if required.

## Step 2: Start a workflow and stop at approval

### What you do

In terminal B, run:

```bash
python -m examples.example03_production_hitl.client start \
  "Prepare the quarterly report"
```

Copy the `Thread ID` printed near the end of the output.

### What you observe

The client displays events in this order:

1. `run_started`, containing an ID beginning with `example03-`.
2. `node_update` for `intake`.
3. `node_update` for `draft`.
4. `approval_required`, containing the draft and the allowed decisions.

Then the client prints `Workflow paused and persisted in ADB.` and exits. It does not submit `approve` or `reject`.

The important observation is that the workflow is now paused in ADB, not held open by the client terminal.

## Step 3: Stop and restart the server

### What you do

In terminal A, press `Ctrl-C` to stop the FastAPI server. Wait for it to stop completely, then run the same command again:

```bash
./examples/example03_production_hitl/start_server.sh
```

Wait for application startup to complete.

### What you observe

The original FastAPI process and its connection pool have been closed. The new process creates a new pool. No command has re-sent the original message and no client process has retained the graph state.

## Step 4: Inspect the paused workflow after restart

### What you do

In terminal B, replace `<thread-id>` with the value copied in step 2:

```bash
python -m examples.example03_production_hitl.client status <thread-id>
```

### What you observe

The command prints JSON with these key values:

```json
{
  "thread_id": "example03-<generated-id>",
  "status": "awaiting_approval",
  "approval_decision": null,
  "approval_required": true
}
```

The `draft` is also present. This observation proves that the new FastAPI instance reconstructed the workflow state from Oracle ADB checkpoints.

## Step 5: Resume the same workflow

### What you do

In terminal B, resume the thread:

```bash
python -m examples.example03_production_hitl.client decide <thread-id> approve
```

You can use `reject` instead, but keep the choice consistent in the following observations.

### What you observe

The client receives an approval-node `node_update`, followed by `run_completed`. The final state reports an `approval_decision` of `approve` and a `status` of `approved`.

The server resumed the paused graph with `Command(resume="approve")` and the original thread ID. It did not start a new workflow.

## Step 6: Confirm the final persisted state

### What you do

Run the status command again:

```bash
python -m examples.example03_production_hitl.client status <thread-id>
```

### What you observe

The response now contains:

```json
{
  "status": "approved",
  "approval_decision": "approve",
  "approval_required": false
}
```

This is the final checkpoint state in ADB. The earlier paused checkpoint remains part of the thread history.

## Step 7: Demonstrate sequential idempotency

### What you do

Repeat the same decision command:

```bash
python -m examples.example03_production_hitl.client decide <thread-id> approve
```

Then try the opposite decision:

```bash
python -m examples.example03_production_hitl.client decide <thread-id> reject
```

### What you observe

The repeated `approve` receives `run_completed` with an `idempotent` value of `true`; the graph is not run a second time. The conflicting `reject` receives HTTP `409 Conflict`, because the durable final state already records approval.

This is sequential idempotency for a completed workflow. Coordinating two simultaneous, conflicting human decisions requires an additional application-level concurrency policy and is outside this example.

## Optional: inspect the checkpoint history in ADB

### What you do

In Database Actions or SQL Developer, run this read-only query:

```sql
SELECT
    checkpoint_id,
    parent_checkpoint_id,
    JSON_SERIALIZE(metadata RETURNING VARCHAR2(4000)) AS metadata_json
FROM checkpoints
WHERE thread_id = '<thread-id>'
ORDER BY checkpoint_id;
```

### What you observe

The result contains checkpoints created before the human pause and additional checkpoints after the decision. The sequence demonstrates durable state transitions for one isolated LangGraph thread.
