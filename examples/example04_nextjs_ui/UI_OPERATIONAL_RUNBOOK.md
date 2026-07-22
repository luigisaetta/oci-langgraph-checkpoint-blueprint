# Example 04 UI Operational Runbook

This runbook demonstrates that a browser UI can display a durable workflow without holding Oracle or LangGraph logic. The persisted state is always recovered through the Example 03 API.

## Before you begin

You need:

* a configured and reachable Example 03 Oracle ADB environment;
* Python environment `oci-langgraph-checkpoint-blueprint` activated for the backend;
* Node.js LTS and npm installed for the Next.js UI;
* `NEXTJS_UI_ORIGIN=http://127.0.0.1:3000` in the root `.env` file; and
* `NEXT_PUBLIC_EXAMPLE03_API_URL=http://127.0.0.1:8081` in `examples/example04_nextjs_ui/.env.local`.

## 1. Start the durable workflow backend

**What you do**

From the repository root, start Example 03:

```bash
conda activate oci-langgraph-checkpoint-blueprint
./examples/example03_production_hitl/start_server.sh
```

In another terminal, verify readiness:

```bash
curl http://127.0.0.1:8081/health/ready
```

**What you observe**

The endpoint returns `{"status":"ready"}`. The FastAPI process has created its ADB pool and initialized the checkpoint schema if necessary.

## 2. Start the Next.js UI

**What you do**

```bash
cd examples/example04_nextjs_ui
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

**What you observe**

The page shows a five-stage workflow timeline and a form prefilled with a deterministic sample message. It has not contacted ADB directly; the only configured service address is the Example 03 API URL.

## 3. Start and pause a workflow

**What you do**

Keep the sample message or enter a new one, then select **Start workflow**.

**What you observe**

The UI shows a generated `example03-...` thread ID and streamed events for `run_started`, `intake`, and `draft`. It then displays an **Approval required** card containing the generated draft. The lifecycle stops at **Awaiting approval**.

## 4. Demonstrate durable state after browser refresh

**What you do**

Copy the thread ID, refresh the browser page, paste the ID into **Load a durable thread**, and select **Load state**.

**What you observe**

The UI restores the paused status and draft. This state comes from `GET /runs/{thread_id}` on Example 03, which reconstructs it from Oracle ADB checkpoints; no browser memory is required.

## 5. Approve or reject the workflow

**What you do**

Select **Approve and resume** or **Reject**.

**What you observe**

The UI consumes the decision SSE stream, renders the final update, and moves the lifecycle to **Completed**. It then reloads the persisted status to display the final decision.

## 6. Verify the final durable state

**What you do**

Refresh the page again, paste the same thread ID, and select **Load state**.

**What you observe**

The final state remains visible with `approved` or `rejected` status and the stored decision. A matching repeated decision is handled by Example 03 as sequential idempotency; simultaneous competing decisions remain outside this example's scope.

## Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| The UI says it cannot reach the workflow service. | Example 03 is not running or the UI API URL is wrong. | Check `/health/ready` and `NEXT_PUBLIC_EXAMPLE03_API_URL`. Restart Next.js after changing `.env.local`. |
| Browser console reports a CORS error. | The origins in the root `.env` and browser URL do not match. | Set `NEXTJS_UI_ORIGIN` to the exact scheme, host, and port used by Next.js, then restart Example 03. |
| `Run not found.` appears after loading a thread. | The thread ID is unknown to the configured ADB schema. | Paste the complete ID from the start event and confirm that both services use the same Example 03 environment. |
| The approval controls are unavailable. | The loaded thread is already terminal or is not waiting for approval. | Start a new run or load a thread whose status is `awaiting_approval`. |
| The UI does not start after `npm install`. | Node.js/npm is unavailable or unsupported locally. | Install a current Node.js LTS release, then rerun the install and quality commands. |
