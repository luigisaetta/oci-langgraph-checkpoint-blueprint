# Specification: Example 04 — IT Procurement Agent and UI

## Status

Accepted

## Context

Example 04 currently demonstrates a Next.js UI over the generic Example 03
workflow API. It must become an independent, concrete durable-workflow example:
an IT procurement agent that searches a deterministic product catalogue and
prepares a simulated purchase order for human approval.

## Scope

Example 04 must contain its own FastAPI/LangGraph agent, based on the durable
pooling and recovery pattern of Example 03, plus its existing Next.js UI. The
agent must accept a natural-language request for IT products (for example,
mouse, keyboard, phone, or battery), find matching catalogue products, create
a deterministic order proposal, pause for approval, and persist the workflow
in Oracle ADB.

The catalogue and order creation are demonstrations only. No supplier API,
payment flow, inventory reservation, or real purchase is in scope.

## Behaviour

1. `POST /runs` creates an `example04-` thread and streams the procurement
   workflow: intake, catalogue search, order proposal, and approval request.
2. The catalogue is in-memory, deterministic, and contains representative IT
   products including mice, keyboards, mobile phones, and batteries.
3. The agent extracts a positive requested quantity when one is present;
   otherwise it proposes one unit. It returns a clear no-match proposal when
   no catalogue product matches.
4. Approval uses the existing `approve` and `reject` decisions. Approval
   records the simulated order as `ordered`; rejection records `rejected`.
5. `GET /runs/{thread_id}` returns the persisted procurement status, proposal,
   selected products, decision, and whether approval is required.
6. `POST /runs/{thread_id}/decision` retains Example 03's sequential
   idempotency behaviour for a repeated final decision. It must not execute the
   graph again for that request.
7. The FastAPI service owns one Oracle pool for its lifespan and calls
   `OracleSaver.setup()` at startup. It uses `EXAMPLE04_SERVER_PORT`, default
   `8082`, and the shared safe ADB and pool configuration.
8. The browser uses only the Example 04 API URL from
   `NEXT_PUBLIC_EXAMPLE04_API_URL`, defaulting to `http://127.0.0.1:8082`.

## Quality and Documentation

1. Python code must have the repository header and Google-style docstrings.
2. Unit tests must cover catalogue matching, quantity handling, no-match
   proposals, status construction, and idempotent decision handling without
   OCI or ADB.
3. The Example 04 README and operational runbook must describe the procurement
   workflow, configuration, local commands, persistence/reload behaviour, and
   the simulated-order boundary.
4. The root README and CHANGELOG must describe Example 04 as an independent IT
   procurement agent.

## Acceptance Criteria

* Example 04 no longer requires the Example 03 service at runtime.
* A request such as `Order 2 wireless mice` produces a persisted purchase-order
  proposal for matching catalogue products and pauses for approval.
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
