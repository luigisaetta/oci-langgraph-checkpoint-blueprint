# Example 01: A Basic LangGraph Flow with Oracle ADB Checkpoints

This first example demonstrates the smallest useful checkpointed LangGraph workflow. A single node converts an input message to uppercase, while Oracle Autonomous Database (ADB) stores the graph execution checkpoints.

It intentionally contains no LLM, tools, or agent loop. The aim is to make the persistence path easy to see and verify before moving to more advanced workflows.

## What the example does

1. Loads local ADB configuration from the repository-root `.env` file.
2. Opens a wallet-based ADB connection.
3. Creates an `OracleSaver` from that connection and calls `setup()`.
4. Builds a one-node LangGraph flow: `START -> uppercase_message -> END`.
5. Compiles the graph with `checkpointer=checkpointer`.
6. Invokes the graph with a new thread ID prefixed with `example01-`.
7. Prints the input and uppercase output.

## Prerequisites

Complete the repository [Quick Start](../../QUICKSTART.md) first. In particular:

* Activate the `oci-langgraph-checkpoint-blueprint` Conda environment.
* Configure `DB_USER`, `DB_PWD`, `WALLET_DIR`, `WALLET_PWD`, and `DB_DSN` in the root `.env` file.
* Confirm the database connection with `python -m test_db_connection`.

The database user requires privileges to create and maintain the checkpoint tables on the first run.

## Run the example

From the repository root:

```bash
python -m examples.example01.run
```

Expected output has this shape:

```text
Example01 flow completed.
  Thread ID: example01-<generated-uuid>
  Input: hello ADB
  Processed output: HELLO ADB
```

## What `setup()` creates

`OracleSaver.setup()` creates or upgrades the checkpoint persistence schema. It is idempotent and should be called before the graph is used. The saver manages these tables in the connected database schema:

| Table | What to inspect |
| --- | --- |
| `checkpoint_migrations` | Schema migration versions applied by the saver. |
| `checkpoints` | One checkpoint record for each persisted graph execution state. |
| `checkpoint_blobs` | Serialized channel values, including state values stored outside the main checkpoint JSON. |
| `checkpoint_writes` | Writes produced by graph tasks while a checkpoint is being persisted. |

Each run uses a distinct `example01-<generated-uuid>` thread ID. Copy the ID printed by the command to focus on one execution, or use the prefix filter below to inspect all Example 01 runs.

## Inspect the checkpoints in ADB

Open SQL Developer or Database Actions with the same database user, then run the following read-only queries.

List the checkpoints produced by this example:

```sql
SELECT
    thread_id,
    checkpoint_ns,
    checkpoint_id,
    parent_checkpoint_id,
    metadata
FROM checkpoints
WHERE thread_id LIKE 'example01-%'
ORDER BY checkpoint_id;
```

Inspect serialized state channels associated with the example thread:

```sql
SELECT
    thread_id,
    checkpoint_ns,
    channel,
    version,
    type
FROM checkpoint_blobs
WHERE thread_id LIKE 'example01-%'
ORDER BY channel, version;
```

Inspect the graph-task writes that contributed to each checkpoint:

```sql
SELECT
    thread_id,
    checkpoint_ns,
    checkpoint_id,
    task_id,
    channel,
    type
FROM checkpoint_writes
WHERE thread_id LIKE 'example01-%'
ORDER BY checkpoint_id, task_id;
```

Do not alter or drop these tables while the example is running. Later examples will build on the same persistence model.

## Oracle reference

This example uses the synchronous `OracleSaver` integration documented in Oracle's [langgraph-oracledb README](https://github.com/oracle/langchain-oracle/tree/main/libs/langgraph-oracledb). The official integration documents `setup()` as the step that creates tables and applies migrations.
