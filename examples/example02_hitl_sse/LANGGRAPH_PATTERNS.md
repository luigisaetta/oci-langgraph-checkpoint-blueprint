# LangGraph Patterns: Oracle ADB Checkpoints and Human-in-the-Loop

This guide isolates the two LangGraph patterns used by Example 02:

1. Persisting graph state in Oracle Autonomous Database (ADB).
2. Pausing a graph for a human decision and resuming the same execution.

The snippets are deliberately small. They show the LangGraph concepts without the FastAPI, Server-Sent Events (SSE), configuration, error-handling, and validation layers used by the runnable example.

Complete the repository [Quick Start](../../QUICKSTART.md) before connecting to ADB. In particular, use the dedicated checkpoint schema owner as `DB_USER`; `OracleSaver.setup()` creates its tables and indexes on the first run.

## Pattern 1: Persist checkpoints in Oracle ADB

Create an Oracle connection, create the saver from that connection, and run `setup()` once before the application accepts work. `setup()` creates or upgrades the checkpoint schema.

```python
import oracledb
from langgraph_oracledb.checkpoint.oracle import OracleSaver

# Supply connection details from secure configuration, never from source code.
connection = oracledb.connect(
    user=db_user,
    password=db_password,
    dsn=db_dsn,
    config_dir=wallet_dir,
    wallet_location=wallet_dir,
    wallet_password=wallet_password,
)

# The saver stores LangGraph checkpoints in this connection's schema.
checkpointer = OracleSaver(connection)

# Safe to call repeatedly: creates tables and applies pending migrations.
checkpointer.setup()
```

Compile the graph with `checkpointer=checkpointer`. A `thread_id` in the invocation configuration identifies one durable workflow execution.

```python
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph


class State(TypedDict, total=False):
    message: str
    result: str
    decision: str


def process(state: State) -> dict[str, str]:
    """A normal graph node; it does not need database-specific code."""
    return {"result": state["message"].upper()}


builder = StateGraph(State)
builder.add_node("process", process)

# This one argument enables durable checkpoint persistence.
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "invoice-review-42"}}
result = graph.invoke({"message": "review this invoice"}, config=config)
```

Keep the thread ID outside the graph state. The same value lets a later invocation load the corresponding persisted state; a different value creates an isolated workflow history.

Close the Oracle connection according to the lifecycle of your application. In a web service, establish and close it per request or use an appropriately managed pool; do not share one connection unsafely across concurrent requests.

## Pattern 2: Pause for a human and resume

Call `interrupt()` inside a node at the exact point where a human decision is needed. LangGraph saves the pause through the configured checkpointer, and returns the supplied dictionary to the caller as interrupt data.

```python
from langgraph.types import interrupt


def request_approval(state: State) -> dict[str, str]:
    """Pause here until a caller resumes this thread with a decision."""
    decision = interrupt(
        {
            "question": "Do you approve this result?",
            "result": state["result"],
            "allowed_decisions": ["approve", "reject"],
        }
    )

    # When the graph resumes, interrupt() returns the supplied decision.
    return {"decision": decision}
```

Build a graph containing the approval node, then invoke it with the same checkpoint-enabled graph:

```python
builder = StateGraph(State)
builder.add_node("process", process)
builder.add_node("approval", request_approval)
builder.add_edge(START, "process")
builder.add_edge("process", "approval")
builder.add_edge("approval", END)
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "invoice-review-42"}}

# The graph runs until request_approval() calls interrupt().
paused = graph.invoke({"message": "review this invoice"}, config=config)
# The returned data includes the question and result for the human interface.
print(paused["__interrupt__"])
```

When the human responds, resume the exact same `thread_id` with `Command(resume=...)`. Do not submit the original input again: the checkpoint already contains the state required to continue.

```python
from langgraph.types import Command

# `invoice-review-42` must be identical to the paused run's thread ID.
completed = graph.invoke(Command(resume="approve"), config=config)
print(completed["decision"])  # "approve"
```

The node containing `interrupt()` begins again on resume, so code before `interrupt()` can run more than once. Keep that code deterministic and avoid non-idempotent side effects before the pause. Perform an irreversible action only after the decision has been returned and validated.

## How this maps to Example 02

The runnable implementation adds a production-oriented HTTP and streaming boundary around these patterns:

| Concern | Complete implementation |
| --- | --- |
| Wallet-based ADB connection and `OracleSaver.setup()` | [app.py](app.py) — `initialize_checkpoint_schema()` |
| Graph construction with `checkpointer=checkpointer` | [graph.py](graph.py) — `build_agent_graph()` |
| Human approval pause and decision validation | [nodes/approval.py](nodes/approval.py) — `ApprovalNode` |
| New thread IDs and resume with `Command(resume=...)` | [app.py](app.py) — API endpoints and `stream_run()` |
| Conversion of graph updates and interrupts to SSE events | [streaming.py](streaming.py) |
| Client that retains the thread ID and submits the decision | [client.py](client.py) |

For the complete server and client instructions, API contract, and SQL verification of pause and resume checkpoints, see the [Example 02 README](README.md).
