# Example 04: Next.js Durable Workflow UI

Example 04 is a browser UI for the durable Human-in-the-Loop workflow exposed by [Example 03](../example03_production_hitl/README.md). It makes the workflow lifecycle visible: start a run, follow its server-sent events, pause for human approval, reload the persisted state, and resume the same thread.

The UI is deliberately a thin client. It communicates only with the Example 03 HTTP/SSE API; it contains no Oracle credentials, `OracleSaver`, LangGraph code, graph state persistence, or direct database access.

```text
Next.js browser UI  -- HTTP/SSE -->  Example 03 FastAPI API  -->  OracleSaver / ADB
```

## What the UI demonstrates

| Capability | What to observe |
| --- | --- |
| Streamed progress | The event timeline receives `run_started`, node updates, an approval request, and completion events from the FastAPI SSE stream. |
| Human approval | The approval card renders the draft and resumes the persisted thread with `approve` or `reject`. |
| Durable reload | Paste a previous thread ID after refreshing the browser to reconstruct its current status through `GET /runs/{thread_id}`. |
| Clear boundaries | The browser knows the FastAPI base URL only. The backend retains responsibility for LangGraph and ADB persistence. |

## Prerequisites

1. Complete the repository [Quick Start](../../QUICKSTART.md) and configure Example 03.
2. Install a current Node.js LTS release with npm.
3. Start Example 03 and confirm its readiness endpoint returns `{"status":"ready"}`.

## Configuration

Example 03 permits one local browser origin through CORS. The root `.env` uses the following default:

```dotenv
NEXTJS_UI_ORIGIN=http://127.0.0.1:3000
```

Copy the UI template and keep the API URL aligned with Example 03:

```bash
cd examples/example04_nextjs_ui
cp .env.local.example .env.local
```

```dotenv
NEXT_PUBLIC_EXAMPLE03_API_URL=http://127.0.0.1:8081
```

`NEXT_PUBLIC_EXAMPLE03_API_URL` is visible to the browser. It must contain only the public FastAPI URL, never ADB credentials or private configuration.

## Run locally

In the first terminal, start the backend from the repository root:

```bash
conda activate oci-langgraph-checkpoint-blueprint
./examples/example03_production_hitl/start_server.sh
```

In a second terminal, install frontend dependencies and start Next.js:

```bash
cd examples/example04_nextjs_ui
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). For the full start, pause, refresh, reload, and resume scenario, follow the [UI Operational Runbook](UI_OPERATIONAL_RUNBOOK.md).

## Quality commands

From `examples/example04_nextjs_ui/`:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

The unit tests mock the HTTP response stream. They do not require FastAPI, OCI, Oracle Database, or ADB.

## Security and production boundary

This UI intentionally does not implement authentication or tenant authorization. A production browser application must enforce identity and thread ownership at the API boundary before it allows a user to read or resume a thread. Refer to the repository-wide [OracleSaver best-practices guide](../../ORACLE_SAVER_BEST_PRACTICES.md) for retention, sensitive-state, idempotency, and concurrency guidance.

## Implementation map

| Concern | File |
| --- | --- |
| Browser UI and lifecycle rendering | [src/app/page.tsx](src/app/page.tsx) |
| UI visual system | [src/app/globals.css](src/app/globals.css) |
| HTTP API client | [src/lib/api.ts](src/lib/api.ts) |
| Native fetch-stream SSE parser | [src/lib/sse.ts](src/lib/sse.ts) |
| Operational demonstration | [UI_OPERATIONAL_RUNBOOK.md](UI_OPERATIONAL_RUNBOOK.md) |
