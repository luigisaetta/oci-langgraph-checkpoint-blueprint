# Example 04 IT Procurement Operational Runbook

This runbook proves that an IT purchase proposal remains durable across a
browser refresh. The workflow is simulated; it never places an external order.

## 1. Start the procurement API

**What you do**

```bash
conda activate oci-langgraph-checkpoint-blueprint
./examples/example04_nextjs_ui/start_server.sh
curl http://127.0.0.1:8082/health/ready
```

**What you observe**

The health endpoint returns `{"status":"ready"}`. Example 04 has created its
own ADB pool and initialized checkpoint storage if needed.

## 2. Start the browser UI

**What you do**

```bash
cd examples/example04_nextjs_ui
cp .env.local.example .env.local
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

**What you observe**

The request field is prefilled with `Order 2 wireless mice`. The browser holds
only the Example 04 API URL, never ADB configuration.

## 3. Search and pause for approval

**What you do**

Select **Search catalogue**.

**What you observe**

The event timeline receives the intake and catalogue-search updates. A new
`example04-...` ID appears, followed by a simulated order for two wireless
mice totaling EUR 58. The workflow pauses at **Awaiting approval**.

## 4. Reload the durable state

**What you do**

Copy the thread ID, refresh the page, paste it in **Load a durable thread**,
and select **Load state**.

**What you observe**

The proposal and approval state return from `GET /runs/{thread_id}` and Oracle
ADB checkpoints. They do not come from browser memory.

## 5. Complete the simulated order

**What you do**

Select **Approve simulated order** or **Reject**.

**What you observe**

The decision stream completes. Approval persists `ordered`; rejection persists
`rejected`. A repeated matching decision returns an idempotent completion
event. This is sequential idempotency, not multi-writer decision arbitration.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Cannot reach procurement service | Confirm Example 04 is running and `NEXT_PUBLIC_EXAMPLE04_API_URL` is `http://127.0.0.1:8082`. |
| CORS error | Set `NEXTJS_UI_ORIGIN` to the exact Next.js browser origin and restart Example 04. |
| No match proposal | Use a supported product: mouse, keyboard, phone, battery, `tastiera`, `cellulare`, or `batterie`. |
| `Run not found.` | Use the complete ID and confirm the API connects to the same ADB schema. |
