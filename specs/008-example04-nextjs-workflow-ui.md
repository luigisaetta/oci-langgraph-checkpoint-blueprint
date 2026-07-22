# Specification: Example 04 — Next.js Durable Workflow UI

## Status

Accepted

## Context

Example 03 proves that a pooled FastAPI service can persist, inspect, and resume a Human-in-the-Loop LangGraph workflow through Oracle ADB. A browser interface should make the same durable workflow visible to developers and stakeholders without moving Oracle or LangGraph concerns into the client.

## Scope

Create `examples/example04_nextjs_ui/` as a standalone Next.js application that communicates only with the Example 03 HTTP and SSE API. It must let a user start a deterministic workflow, follow streamed progress, inspect persisted status, submit an approval decision, and reload an existing thread.

The UI is a demonstration client. Oracle ADB access, `OracleSaver`, graph creation, checkpoint schema setup, and LangGraph resume execution remain exclusively in Example 03.

## API Boundary

1. The UI must read the Example 03 base URL from the public `NEXT_PUBLIC_EXAMPLE03_API_URL` environment variable, defaulting to `http://127.0.0.1:8081` for local development.
2. It must call only these endpoints:
   * `POST /runs` to start a run and consume its SSE response.
   * `GET /runs/{thread_id}` to retrieve persisted status.
   * `POST /runs/{thread_id}/decision` to submit `approve` or `reject` and consume its SSE response.
3. The UI must not import `oracledb`, `langgraph`, `langgraph_oracledb`, or Python modules; it must not contain ADB credentials or database connection configuration.
4. Example 03 must allow the configured local Next.js development origin through explicit CORS configuration. It must not use an unrestricted `*` origin when credentials are enabled.

## User Experience

1. The landing view must explain the durable-workflow demonstration and show a form for an initial message.
2. Starting a run must display the generated thread ID and a chronological event timeline from the SSE stream.
3. A visible workflow timeline must represent the lifecycle: `Started`, `Intake`, `Draft`, `Awaiting approval`, and `Completed`.
4. On an `approval_required` event, the UI must show the persisted draft and `Approve` and `Reject` controls.
5. A user must be able to paste a thread ID and load its persisted status. A page reload followed by that action must reconstruct the visible state through Example 03, not browser-only state.
6. The UI must show safe, actionable errors for rejected HTTP requests, malformed SSE payloads, and unreachable API service. It must not expose database credentials or raw stack traces.
7. While a start or decision stream is active, controls that would start another action for that displayed thread must be disabled.

## Implementation and Quality Requirements

1. Use Next.js with TypeScript and the App Router. Keep browser interaction in a client component and keep HTTP/SSE parsing in a testable TypeScript module.
2. Use native browser `fetch` streaming; do not introduce an SSE client dependency solely for this example.
3. Define TypeScript types for Example 03 status data and named SSE event payloads.
4. Include unit tests for the SSE parser and the API client request/response behaviour without a live FastAPI, Oracle, OCI, or ADB resource.
5. Provide `package.json` commands for development, production build, linting, type checking, and tests.
6. Provide an operational Markdown runbook documenting prerequisites, configuration, terminal commands, browser flow, persisted-state reload, and troubleshooting. All documentation must be in English.
7. Link Example 04 from the root README and record it in `CHANGELOG.md`.

## Acceptance Criteria

* The Next.js project builds successfully with its declared dependencies.
* Its code does not contain Oracle database credentials or direct Oracle/LangGraph imports.
* The UI can start Example 03, render its named SSE events, pause for approval, submit a decision, and render completion.
* Loading a known thread ID renders the status returned by `GET /runs/{thread_id}`.
* The browser may be served from the documented local origin without a CORS failure.
* Unit tests cover SSE event parsing, successful status retrieval, and an HTTP error path.
* The operational runbook permits a developer to run both services and observe durable state after a browser refresh.

## Out of Scope

* User authentication, tenant isolation, and production authorization policy.
* Direct ADB access, Oracle SQL views, and checkpoint management from the browser.
* A real LLM provider or production agent UX.
* Distributed locking or conflict arbitration for simultaneous decisions.
* OCI deployment configuration for the Next.js application.
