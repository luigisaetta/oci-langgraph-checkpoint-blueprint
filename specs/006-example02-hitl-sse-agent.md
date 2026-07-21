# Specification: Example 02 — Human-in-the-Loop Agent with SSE

## Status

Accepted

## Context

Example 01 established basic, durable LangGraph checkpoints in Oracle Autonomous Database (ADB). The next example must demonstrate a practical enterprise pattern: a workflow that pauses for a human decision and resumes from its persisted checkpoint while reporting progress to a client in real time.

## Scope

Create `examples/example02_hitl_sse/`, containing a deterministic LangGraph agent exposed through FastAPI. It must stream server-sent events (SSE), pause with LangGraph human-in-the-loop (HITL) functionality, and resume the same persisted ADB thread after an approval or rejection.

## Dependencies

The Conda environment must explicitly include:

* `fastapi` for the HTTP API.
* `uvicorn` for the ASGI development server.
* `httpx` for the streaming Python client.

## Graph Contract

1. Define an `AgentState` with the input message, normalized message, draft, status, and approval decision.
2. Implement exactly three graph nodes as separate classes in separate modules. Every class must implement `__call__(state)` so its instance is directly usable as a LangGraph node callable:
   * `IntakeNode` normalizes and accepts the input.
   * `DraftNode` creates a deterministic draft from the normalized input.
   * `ApprovalNode` calls LangGraph `interrupt()` with an approval request containing the draft.
3. Compile the graph with Oracle's `OracleSaver` and persist checkpoints in ADB.
4. Initialize the Oracle checkpoint schema with `OracleSaver.setup()` on application startup.
5. Generate a unique `example02-` thread ID when a run starts. Resume must use that same thread ID.
6. On resume, `Command(resume="approve")` or `Command(resume="reject")` must become the return value of `interrupt()` and update the final agent state.

## FastAPI and SSE Contract

1. Provide `POST /runs` accepting a JSON body with `message` and returning `text/event-stream`.
2. Provide `POST /runs/{thread_id}/decision` accepting only `approve` or `reject` and returning `text/event-stream`.
3. Stream SSE events in this order where applicable:
   * `run_started` with the thread ID;
   * `node_update` after each completed node;
   * `approval_required` when the graph interrupts;
   * `run_completed` once the graph reaches the end; or
   * `error` for safe, actionable failures.
4. SSE payloads must be JSON and must never include `DB_PWD` or `WALLET_PWD`.

## Client Contract

1. Provide a Python client runnable from the repository root.
2. The client must display a concise workflow timeline alongside each streamed event payload, followed by a blank line for readability. The timeline must identify completion of Intake, Draft, and Approval as steps 1/3, 2/3, and 3/3; clearly identify when human approval is pending; and report workflow completion or an error. Before connecting, it must display a titled header containing the API URL and the non-sensitive `DB_USER`, `DB_DSN`, and `WALLET_DIR` local configuration values.
3. On `approval_required`, it must prompt the user for `approve` or `reject`.
4. It must call the decision endpoint with the original thread ID and display the resumed stream until completion.

## Documentation and Testing

1. The example README must document setup, server and client commands, API endpoints, the HITL lifecycle, thread persistence, and ADB inspection queries. It must include a step-by-step procedure for verifying the persisted approval pause and the final checkpoint after a decision.
2. Unit tests must validate node transformations, interrupt/resume behaviour with an in-memory saver, SSE formatting, and API request validation without requiring OCI or ADB.
3. The main README must link to Example 02, and `CHANGELOG.md` must record the feature.

## Acceptance Criteria

* The initial graph run reaches `approval_required` after the first two node updates.
* Resuming the same thread with `approve` reaches `run_completed` and produces an approved final state.
* Resuming with `reject` produces a rejected final state.
* The Python client uses the exact thread ID emitted by `run_started` when submitting the decision.
* All automated tests run without live OCI or ADB access.
