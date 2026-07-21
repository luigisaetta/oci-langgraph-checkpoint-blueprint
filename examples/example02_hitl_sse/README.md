# Example 02: Human-in-the-Loop Agent with FastAPI SSE

This example builds on Example 01 by exposing a durable LangGraph agent through a FastAPI API. The agent streams progress with server-sent events (SSE), pauses for a human approval decision, and resumes the same Oracle Autonomous Database (ADB) checkpoint thread.

The workflow is deterministic on purpose: it makes the Human-in-the-Loop (HITL), persistence, streaming, and API boundaries easy to inspect without requiring an LLM provider.

## Agent flow

```text
START
  |
  v
IntakeNode(state)
  |
  v
DraftNode(state)
  |
  v
ApprovalNode(state)
  |  interrupt() -> approval_required SSE event
  |  Command(resume="approve" | "reject")
  v
END
```

Each node is a separate callable class: it implements `__call__(state)` and is registered directly with LangGraph.

| Node | Responsibility |
| --- | --- |
| `IntakeNode` | Trims and validates the input message. |
| `DraftNode` | Produces a deterministic draft for review. |
| `ApprovalNode` | Pauses the graph with `interrupt()` until a human approves or rejects the draft. |

## Prerequisites

Complete the repository [Quick Start](../../QUICKSTART.md) first. The same root `.env` and ADB wallet configuration are used here. The ADB user needs permission to create the checkpoint tables the first time the API starts.

## Start the API

From the repository root, activate the environment and start the development server:

```bash
conda activate oci-langgraph-checkpoint-blueprint
uvicorn examples.example02_hitl_sse.app:app --reload
```

At startup, `OracleSaver.setup()` creates or upgrades the ADB checkpoint schema. Each API stream opens a wallet-based ADB connection and compiles the graph with `OracleSaver`.

## Run the Python client

In a second terminal, from the repository root:

```bash
conda activate oci-langgraph-checkpoint-blueprint
python -m examples.example02_hitl_sse.client "Prepare the quarterly report"
```

The client displays streamed node updates. When it receives `approval_required`, it displays the draft and asks for one of these values:

```text
Decision [approve/reject]: approve
```

It submits that decision with the original thread ID, allowing LangGraph to load the ADB checkpoint and resume the paused `ApprovalNode`.

## API contract

### Start a run

```http
POST /runs
Content-Type: application/json

{"message": "Prepare the quarterly report"}
```

The response is `text/event-stream`. The first event includes a unique thread ID with the prefix `example02-`.

### Resume after approval

```http
POST /runs/{thread_id}/decision
Content-Type: application/json

{"decision": "approve"}
```

Only `approve` and `reject` are accepted. The same `thread_id` is required because it identifies the persisted LangGraph state to resume.

## SSE events

| Event | Meaning |
| --- | --- |
| `run_started` | A new thread ID was generated. |
| `node_update` | One node returned a state update. |
| `approval_required` | The graph reached `interrupt()` and is waiting for a decision. |
| `run_completed` | The resumed agent reached `END`; the event contains final state. |
| `error` | A safe configuration or execution error occurred. |

## Inspect the HITL checkpoints in ADB

The Oracle saver uses the same `checkpoint_migrations`, `checkpoints`, `checkpoint_blobs`, and `checkpoint_writes` tables described in Example 01. An interrupted run produces additional snapshots because LangGraph persists state both before and after node boundaries, including the pause location.

List the checkpoint lifecycle for all Example 02 threads:

```sql
SELECT
    thread_id,
    checkpoint_ns,
    checkpoint_id,
    parent_checkpoint_id,
    JSON_SERIALIZE(metadata RETURNING VARCHAR2(4000)) AS metadata_json
FROM checkpoints
WHERE thread_id LIKE 'example02-%'
ORDER BY thread_id, checkpoint_id;
```

After the client sends a decision, query the same thread ID again. The final checkpoint state includes `approval_decision` and a `status` of `approved` or `rejected`.

## Verify the approval pause and final checkpoint step by step

Use this procedure to observe the durable HITL lifecycle in ADB. Replace `<thread-id>` with the ID emitted by the client's `run_started` event.

### 1. Start a run and wait at the approval prompt

Start the API, then run the Python client as described above. Let the client reach this prompt, but do **not** enter a decision yet:

```text
Decision [approve/reject]:
```

At this point, the API has streamed `approval_required` and the graph is paused in `ApprovalNode`. Copy the `example02-...` thread ID from the earlier `run_started` event.

### 2. Verify the persisted approval state

In SQL Developer or Database Actions, run this read-only query:

```sql
SELECT
    checkpoint_id,
    JSON_VALUE(
        checkpoint,
        '$.channel_values.status' RETURNING VARCHAR2(50)
    ) AS status,
    JSON_VALUE(
        checkpoint,
        '$.channel_values.draft' RETURNING VARCHAR2(4000)
    ) AS draft,
    JSON_VALUE(
        checkpoint,
        '$.channel_values.approval_decision' RETURNING VARCHAR2(20)
    ) AS approval_decision
FROM checkpoints
WHERE thread_id = '<thread-id>'
ORDER BY checkpoint_id DESC
FETCH FIRST 1 ROW ONLY;
```

Observe these values in the latest checkpoint:

| Column | Expected value while paused |
| --- | --- |
| `status` | `awaiting_approval` |
| `draft` | The deterministic draft displayed by the client. |
| `approval_decision` | `NULL`, because no human decision has been supplied yet. |

LangGraph also persists the interrupt as a pending write. Confirm it with:

```sql
SELECT
    checkpoint_id,
    task_id,
    channel,
    type
FROM checkpoint_writes
WHERE thread_id = '<thread-id>'
  AND channel = '__interrupt__'
ORDER BY checkpoint_id, task_id;
```

At least one row confirms that the `interrupt()` call was durably saved for the thread.

### 3. Submit the human decision

Return to the client terminal and enter either `approve` or `reject`. The client calls `POST /runs/{thread_id}/decision`, and the API resumes the same thread with `Command(resume=...)`.

Wait for the `run_completed` SSE event.

### 4. Verify the final checkpoint

Run this query against the same thread:

```sql
SELECT
    checkpoint_id,
    JSON_VALUE(
        checkpoint,
        '$.channel_values.status' RETURNING VARCHAR2(50)
    ) AS status,
    JSON_VALUE(
        checkpoint,
        '$.channel_values.approval_decision' RETURNING VARCHAR2(20)
    ) AS approval_decision
FROM checkpoints
WHERE thread_id = '<thread-id>'
ORDER BY checkpoint_id DESC
FETCH FIRST 1 ROW ONLY;
```

The latest checkpoint is the completed state. It must show one of these consistent pairs:

| Submitted decision | `status` | `approval_decision` |
| --- | --- | --- |
| `approve` | `approved` | `approve` |
| `reject` | `rejected` | `reject` |

The original pause checkpoint remains in the history, while this newer checkpoint proves that the persisted workflow resumed and reached `END`.

## LangGraph and Oracle references

This example uses Oracle's [langgraph-oracledb integration](https://github.com/oracle/langchain-oracle/tree/main/libs/langgraph-oracledb) for `OracleSaver`. Its HITL flow follows the LangGraph pattern of pausing with [`interrupt()` and resuming with `Command(resume=...)`](https://docs.langchain.com/oss/python/langgraph/graph-api), while node updates are surfaced through [LangGraph streaming](https://docs.langchain.com/oss/python/langgraph/streaming).
