# Example 04: Durable IT Procurement Agent and UI

Example 04 is an independent, concrete LangGraph demonstration. A FastAPI
procurement agent searches a small deterministic IT catalogue, creates a
simulated purchase-order proposal, pauses for a human decision, and persists
every state transition in Oracle ADB. Its Next.js UI consumes only this
example's HTTP/SSE API.

```text
Next.js UI -> Example 04 FastAPI -> LangGraph / OracleSaver -> Oracle ADB
```

The demonstration never calls a supplier, reserves stock, charges a payment
method, or creates a real order.

## Catalogue and workflow

The embedded catalogue includes a wireless mouse, wireless keyboard, business
phone, and USB-C battery pack. Requests may be English or use the Italian
terms `tastiera`, `cellulare`, and `batterie`. A quantity such as `2` is used;
otherwise the proposal defaults to one unit.

For example, `Order 2 wireless mice` produces a EUR 58 simulated proposal.
The durable lifecycle is **Started → Intake → Order proposal → Awaiting
approval → Order completed**. Approving records `ordered`; rejecting records
`rejected`.

## Configuration

Complete the repository [Quick Start](../../QUICKSTART.md). In the root `.env`,
configure the normal ADB wallet variables and the shared pool variables
`DB_POOL_MIN`, `DB_POOL_MAX`, and `DB_POOL_INCREMENT`. Also set these values:

| Variable | Required | Purpose | Safe example |
| --- | --- | --- | --- |
| `EXAMPLE04_SERVER_PORT` | No | API port. | `8082` |
| `NEXTJS_UI_ORIGIN` | No | Exact permitted browser origin. | `http://127.0.0.1:3000` |
| `NEXT_PUBLIC_EXAMPLE04_API_URL` | No | Browser-visible API base URL in `.env.local`. | `http://127.0.0.1:8082` |

Copy `.env.local.example` to `.env.local` in this directory. It contains no
ADB credentials. The Python service uses the existing validated, wallet-based
pool configuration pattern from Example 03, but owns its own pool and
`example04-` checkpoint threads.

## Run locally

Start the procurement API from the repository root:

```bash
conda activate oci-langgraph-checkpoint-blueprint
./examples/example04_nextjs_ui/start_server.sh
curl http://127.0.0.1:8082/health/ready
```

Then run the browser UI:

```bash
cd examples/example04_nextjs_ui
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000), submit an IT request,
and approve or reject the proposal. To prove durable recovery, refresh the
page, paste the displayed `example04-...` thread ID, and select **Load state**.
The detailed walkthrough is in the [UI Operational Runbook](UI_OPERATIONAL_RUNBOOK.md).

## API and idempotency

| Endpoint | Purpose |
| --- | --- |
| `GET /health/ready` | Validates an acquired ADB pool connection. |
| `POST /runs` | Starts and streams a procurement workflow. |
| `GET /runs/{thread_id}` | Reconstructs durable procurement state from ADB. |
| `POST /runs/{thread_id}/decision` | Approves or rejects the persisted proposal. |

Repeating the same final decision returns an idempotent `run_completed` event
without executing the graph a second time. Simultaneous conflicting decisions,
authorization, budgets, and real purchasing policy are outside this example.

## Quality commands

```bash
black examples/example04_nextjs_ui
pylint examples/example04_nextjs_ui
pytest examples/example04_nextjs_ui/tests --cov=examples.example04_nextjs_ui
npm run lint
npm run typecheck
npm test
npm run build
```
