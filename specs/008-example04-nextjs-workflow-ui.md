# Specification: Example 04 — IT Procurement Agent and UI

## Status

Accepted

## Context

Example 04 currently demonstrates a Next.js UI over the generic Example 03
workflow API. It must become an independent, concrete durable-workflow example:
an IT procurement agent that uses an LLM to interpret a request and prepares a
simulated purchase order for human approval.

## Scope

Example 04 must live in `examples/example04_it_procurement/`, with a `backend/`
directory for its FastAPI/LangGraph agent and a `frontend/` directory for its
Next.js UI. The agent is based on the durable pooling and recovery pattern of
Example 03. The
agent must use OCI Generative AI's OpenAI-compatible Responses API to extract a
structured IT procurement request and generate a simulated offer, pause for
approval, and persist the workflow in Oracle ADB.

The catalogue search and order creation are simulations only. No supplier API,
payment flow, inventory reservation, or real purchase is in scope.

## Behaviour

1. `POST /runs` creates an `example04-` thread and streams the procurement
   workflow: request extraction, offer generation, and approval request.
2. The intake node calls the Responses API with a strict JSON Schema and stores
   `requested_object` and `quantity`. Quantity must be an integer from 1 to 99;
   the model is instructed to use one when omitted.
3. The offer-generation node calls the Responses API with that structured JSON.
   Its prompt must generate a concise illustrative EUR offer and must prohibit
   claims of real supplier access, inventory reservation, or order creation.
4. Approval uses the existing `approve` and `reject` decisions. Approval
   records the simulated order as `ordered`; rejection records `rejected`.
5. `GET /runs/{thread_id}` returns the persisted procurement status, proposal,
   extracted object, quantity, decision, and whether approval is required.
6. `POST /runs/{thread_id}/decision` retains Example 03's sequential
   idempotency behaviour for a repeated final decision. It must not execute the
   graph again for that request.
7. The FastAPI service owns one Oracle pool for its lifespan and calls
   `OracleSaver.setup()` at startup. It uses `EXAMPLE04_SERVER_PORT`, default
   `8082`, and the shared safe ADB and pool configuration.
8. The backend creates its OCI client in a dedicated factory using
   `GENAI_API_KEY`, `REGION`, and optional `OCI_MODEL_ID`. It must derive the
   OCI endpoint as `https://inference.generativeai.<region>.oci.oraclecloud.com/openai/v1`.
9. The browser uses only the Example 04 API URL from
   `NEXT_PUBLIC_EXAMPLE04_API_URL`, defaulting to `http://127.0.0.1:8082`.

## Quality and Documentation

1. Python code must have the repository header and Google-style docstrings.
2. Unit tests must cover strict structured request parsing, invalid model
   output, generated offer handling, OCI endpoint creation, status construction,
   and idempotent decision handling without OCI or ADB.
3. The Example 04 README and operational runbook must describe the procurement
   workflow, configuration, local commands, persistence/reload behaviour, and
   the simulated-order boundary.
4. The root README and CHANGELOG must describe Example 04 as an independent IT
   procurement agent.
5. The Example 04 parent README and operational runbook remain at the parent
   directory. Backend Python tests live in `backend/tests/`; frontend package
   files, source code, and TypeScript tests live in `frontend/`.

## Acceptance Criteria

* Example 04 no longer requires the Example 03 service at runtime.
* A request such as `Order 2 wireless mice` produces the persisted structured
  JSON `{"requested_object": "...", "quantity": 2}`, then a simulated offer,
  and pauses for approval.
* A browser refresh followed by loading a known `example04-` thread reconstructs
  its state through the Example 04 API.
* Approval records an `ordered` terminal status; rejection records `rejected`.
* No real ordering, credentials, supplier integration, or database access is
  present in the browser code.

## Out of Scope

* Real suppliers, pricing feeds, payment, stock reservation, and fulfilment.
* Authentication, authorization, budgets, and enterprise purchasing policy.
* Distributed arbitration for simultaneous conflicting decisions.
* OCI deployment configuration.
