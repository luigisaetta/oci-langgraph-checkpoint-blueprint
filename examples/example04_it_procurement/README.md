# Example 04: Durable IT Procurement Agent and UI

Example 04 is an independent, concrete LangGraph demonstration. A FastAPI
procurement agent uses OCI Generative AI's OpenAI-compatible Responses API to
extract a structured IT request and generate a simulated purchase-order offer,
then pauses for a human decision and persists every state transition in Oracle
ADB. Its Next.js UI consumes only this example's HTTP/SSE API.

```text
Next.js UI -> Example 04 FastAPI -> LangGraph / OracleSaver -> Oracle ADB
```

The demonstration never calls a supplier, reserves stock, charges a payment
method, or creates a real order.

## LLM-assisted workflow

The first node sends the natural-language request to an OCI Responses API call
with strict structured output. The persisted JSON has this shape:

```json
{
  "requested_object": "wireless ergonomic mouse",
  "quantity": 2
}
```

The second node sends exactly that JSON to a separate OCI Responses API call.
It produces a concise illustrative offer in EUR, with an explicit availability
assumption. The prompt forbids claims that a real supplier or inventory system
was contacted.

For example, `Order 2 wireless mice` is extracted as a request for two mice and
then produces an LLM-generated simulated proposal.
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
| `GENAI_API_KEY` | Yes | OCI Generative AI API key used by the backend only. | Leave empty in `.env.sample`. |
| `REGION` | Yes | OCI region used to derive the inference endpoint. | `eu-frankfurt-1` |
| `OCI_MODEL_ID` | No | OCI hosted Responses API model ID. | `openai.gpt-5.5` |

Copy `frontend/.env.local.example` to `frontend/.env.local`. It contains no
ADB credentials. Set `GENAI_API_KEY` only in the root local `.env`; never
commit it. The backend factory derives the OCI endpoint as
`https://inference.generativeai.<REGION>.oci.oraclecloud.com/openai/v1`. The
Python service uses the existing validated, wallet-based pool configuration
pattern from Example 03, but owns its own pool and `example04-` checkpoint
threads.

## Run locally

Start the procurement API from the repository root:

```bash
conda activate oci-langgraph-checkpoint-blueprint
./examples/example04_it_procurement/backend/start_server.sh
curl http://127.0.0.1:8082/health/ready
```

Then run the browser UI:

```bash
cd examples/example04_it_procurement/frontend
npm install
npm run dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000), submit an IT request,
and approve or reject the proposal. To prove durable recovery, refresh the
page, paste the displayed `example04-...` thread ID, and select **Load state**.
The original request is restored into the request field along with the durable
status. The detailed walkthrough is in the [UI Operational Runbook](UI_OPERATIONAL_RUNBOOK.md).

The **Process instances** page (`/runs`) lists the persisted `example04-`
process IDs, submission date/time, and whether each workflow is **In progress**
or **Completed**. Instances are ordered from most recently submitted to oldest.
The browser obtains this information only from the backend, which reads the
latest checkpoint for each Example 04 thread.

Select a Process ID to open `/runs/{thread_id}`. The detail view reconstructs
the original request, extracted item and quantity, simulated offer, lifecycle
status, and approval decision through the existing `GET /runs/{thread_id}` API.
Each row also has a browser-only **Copy ID** action.

## API and idempotency

| Endpoint | Purpose |
| --- | --- |
| `GET /health/ready` | Validates an acquired ADB pool connection. |
| `POST /runs` | Starts and streams a procurement workflow. |
| `GET /runs` | Lists process IDs, submission timestamps, and current UI status, newest first. |
| `GET /runs/{thread_id}` | Reconstructs durable procurement state from ADB. |
| `POST /runs/{thread_id}/decision` | Approves or rejects the persisted proposal. |

Repeating the same final decision returns an idempotent `run_completed` event
without executing the graph a second time. Simultaneous conflicting decisions,
authorization, budgets, and real purchasing policy are outside this example.

## Quality commands

```bash
black examples/example04_it_procurement/backend
pylint examples/example04_it_procurement/backend
pytest examples/example04_it_procurement/backend/tests --cov=examples.example04_it_procurement.backend
cd examples/example04_it_procurement/frontend
npm run lint
npm run typecheck
npm test
npm run build
```
