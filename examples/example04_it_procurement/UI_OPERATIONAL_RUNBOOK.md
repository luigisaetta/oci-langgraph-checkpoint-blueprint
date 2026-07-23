# Example 04 IT Procurement Operational Runbook

This runbook proves that an IT purchase proposal remains durable across a
browser refresh. The workflow is simulated; it never places an external order.

## 1. Start the procurement API

**What you do**

```bash
conda activate oci-langgraph-checkpoint-blueprint
./examples/example04_it_procurement/backend/start_server.sh
curl http://127.0.0.1:8082/health/ready
```

**What you observe**

The health endpoint returns `{"status":"ready"}`. Example 04 has created its
own ADB pool and initialized checkpoint storage if needed.

## 2. Start the browser UI

**What you do**

```bash
cd examples/example04_it_procurement/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

**What you observe**

The request field is prefilled with `Order 2 wireless mice`. The browser holds
only the Example 04 API URL, never ADB or OCI API-key configuration.

## 3. View process instances

**What you do**

Select **Process instances** in the navigation.

**What you observe**

The page lists every persisted `example04-...` process ID, its submission
date/time, and a current status: **In progress** for non-terminal workflows
and **Completed** for workflows that were approved or rejected. The newest
submissions appear first. Select **Refresh** to retrieve the latest list from
`GET /runs`.

Select a Process ID to open its detail view. It displays the original request,
the extracted item and quantity, simulated offer, lifecycle status, and any
approval decision reconstructed through `GET /runs/{thread_id}`. Select
**Copy ID** to copy the process ID to the browser clipboard.

## 4. Search and pause for approval

**What you do**

Select **Search catalogue**.

**What you observe**

The event timeline receives the request-extraction and offer-generation updates.
A new `example04-...` ID appears, followed by an LLM-generated simulated offer.
The workflow pauses at **Awaiting approval**.

## 5. Reload the durable state

**What you do**

Copy the thread ID, refresh the page, paste it in **Load a durable thread**,
and select **Load state**.

**What you observe**

The proposal and approval state return from `GET /runs/{thread_id}` and Oracle
ADB checkpoints. They do not come from browser memory.

## 6. Complete the simulated order

**What you do**

Select **Approve** or **Reject**.

**What you observe**

The decision stream completes. Approval persists `ordered`; rejection persists
`rejected`. A repeated matching decision returns an idempotent completion
event. This is sequential idempotency, not multi-writer decision arbitration.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Cannot reach procurement service | Confirm Example 04 is running and `NEXT_PUBLIC_EXAMPLE04_API_URL` is `http://127.0.0.1:8082`. |
| CORS error | Set `NEXTJS_UI_ORIGIN` to the exact Next.js browser origin and restart Example 04. |
| LLM execution error | Verify `GENAI_API_KEY`, `REGION`, and `OCI_MODEL_ID` in the root `.env`, then restart Example 04. |
| `Run not found.` | Use the complete ID and confirm the API connects to the same ADB schema. |
