"use client";

import { FormEvent, useMemo, useState } from "react";

import {
  getRunStatus,
  startRun,
  submitDecision,
  WorkflowApiError,
} from "../lib/api";
import type { Decision, RunStatus, WorkflowEvent } from "../lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_EXAMPLE04_API_URL ?? "http://127.0.0.1:8082";

const workflowStages = [
  { key: "started", label: "Started" },
  { key: "intake", label: "Intake" },
  { key: "draft", label: "Order proposal" },
  { key: "awaiting", label: "Awaiting approval" },
  { key: "completed", label: "Order completed" },
] as const;

type StageKey = (typeof workflowStages)[number]["key"];

interface TimelineEntry {
  name: string;
  summary: string;
}

function asText(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function errorMessage(error: unknown): string {
  if (error instanceof WorkflowApiError || error instanceof Error) {
    return error.message;
  }
  return "The workflow UI encountered an unexpected error.";
}

function stageFromStatus(status: RunStatus): StageKey {
  if (status.status === "awaiting_approval") {
    return "awaiting";
  }
  if (status.status === "ordered" || status.status === "rejected") {
    return "completed";
  }
  return "started";
}

function eventSummary(event: WorkflowEvent): string {
  if (event.name === "node_update") {
    return `Completed ${asText(event.payload.node) ?? "workflow"} node.`;
  }
  if (event.name === "approval_required") {
    return "The workflow is paused and waiting for a human decision.";
  }
  if (event.name === "run_completed") {
    return "The simulated purchase order reached a final state.";
  }
  if (event.name === "run_started") {
    return "A new durable workflow thread was created.";
  }
  if (event.name === "error") {
    return asText(event.payload.message) ?? "The workflow service reported an error.";
  }
  return "Received a workflow event.";
}

export default function HomePage() {
  const [message, setMessage] = useState("Order 2 wireless mice");
  const [threadInput, setThreadInput] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [stage, setStage] = useState<StageKey>("started");
  const [events, setEvents] = useState<TimelineEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeStageIndex = useMemo(
    () => workflowStages.findIndex((candidate) => candidate.key === stage),
    [stage],
  );

  function applyEvent(event: WorkflowEvent): void {
    const eventThreadId = asText(event.payload.thread_id);
    if (eventThreadId) {
      setThreadId(eventThreadId);
      setThreadInput(eventThreadId);
    }
    if (event.name === "run_started") {
      setStage("started");
    }
    if (event.name === "node_update") {
      const node = asText(event.payload.node);
      if (node === "intake") {
        setStage("intake");
      }
      if (node === "offer_generation") {
        setStage("draft");
      }
    }
    if (event.name === "approval_required") {
      const request = event.payload.request;
      if (request && typeof request === "object") {
        setDraft(asText((request as Record<string, unknown>).draft));
      }
      setStage("awaiting");
    }
    if (event.name === "run_completed") {
      const state = event.payload.state;
      if (state && typeof state === "object") {
        const values = state as Record<string, unknown>;
        const status = asText(values.status);
        const finalDraft = asText(values.draft);
        const approvalDecision = asText(values.approval_decision);
        const finalThreadId = eventThreadId ?? threadId;
        if (finalThreadId && status) {
          setRunStatus({
            thread_id: finalThreadId,
            status,
            draft: finalDraft,
            requested_object: null,
            quantity: null,
            approval_decision:
              approvalDecision === "approve" || approvalDecision === "reject"
                ? approvalDecision
                : null,
            approval_required: status === "awaiting_approval",
          });
        }
        setDraft(finalDraft);
      }
      setStage("completed");
    }
    if (event.name === "error") {
      setError(eventSummary(event));
    }
    setEvents((currentEvents) => [
      ...currentEvents,
      { name: event.name, summary: eventSummary(event) },
    ]);
  }

  async function handleStart(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!message.trim()) {
      setError("Enter a message before starting the workflow.");
      return;
    }
    setError(null);
    setIsStreaming(true);
    setThreadId(null);
    setRunStatus(null);
    setDraft(null);
    setStage("started");
    setEvents([]);
    try {
      await startRun(API_URL, message.trim(), applyEvent);
    } catch (caughtError) {
      setError(errorMessage(caughtError));
    } finally {
      setIsStreaming(false);
    }
  }

  async function handleLoad(): Promise<void> {
    const requestedThreadId = threadInput.trim();
    if (!requestedThreadId) {
      setError("Paste a thread ID to load its persisted state.");
      return;
    }
    setError(null);
    try {
      const loadedStatus = await getRunStatus(API_URL, requestedThreadId);
      setThreadId(loadedStatus.thread_id);
      setRunStatus(loadedStatus);
      setDraft(loadedStatus.draft);
      setStage(stageFromStatus(loadedStatus));
      setEvents([
        {
          name: "persisted_status",
          summary: "Loaded the current state from the Example 04 procurement API.",
        },
      ]);
    } catch (caughtError) {
      setError(errorMessage(caughtError));
    }
  }

  async function handleDecision(decision: Decision): Promise<void> {
    if (!threadId) {
      return;
    }
    setError(null);
    setIsStreaming(true);
    try {
      await submitDecision(API_URL, threadId, decision, applyEvent);
      const loadedStatus = await getRunStatus(API_URL, threadId);
      setRunStatus(loadedStatus);
      setDraft(loadedStatus.draft);
      setStage(stageFromStatus(loadedStatus));
    } catch (caughtError) {
      setError(errorMessage(caughtError));
    } finally {
      setIsStreaming(false);
    }
  }

  const approvalRequired =
    stage === "awaiting" || runStatus?.approval_required === true;

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Example 04 · IT procurement agent</p>
        <h1>IT procurement, made durable.</h1>
        <p className="hero-copy">
          Search the demo IT catalogue, review a simulated purchase order, then
          pause, reload, and resume it. Durable state remains in <span>Oracle</span>{" "}
          ADB through the backend.
        </p>
      </section>

      <section className="workflow-card" aria-label="Durable workflow controls">
        <div className="workflow-heading">
          <div>
            <p className="section-label">Live workflow</p>
            <h2>Start a procurement request</h2>
          </div>
          <span className={isStreaming ? "status streaming" : "status"}>
            {isStreaming ? "Streaming" : "Ready"}
          </span>
        </div>

        <form onSubmit={handleStart} className="start-form">
          <label htmlFor="message">IT product request</label>
          <div className="form-row">
            <input
              id="message"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              maxLength={2000}
              disabled={isStreaming}
            />
            <button type="submit" disabled={isStreaming}>
              Search catalogue
            </button>
          </div>
        </form>

        <div className="stage-list" aria-label="Workflow lifecycle">
          {workflowStages.map((workflowStage, index) => (
            <div
              className={
                index <= activeStageIndex ? "stage complete" : "stage"
              }
              key={workflowStage.key}
            >
              <span>{index + 1}</span>
              <p>{workflowStage.label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="workspace">
        <div className="panel persisted-panel">
          <p className="section-label">Persisted run</p>
          <h2>Load a durable thread</h2>
          <p className="muted">
            Refreshing this page does not lose the request. Paste its thread ID
            to reconstruct the current state through Example 04.
          </p>
          <div className="load-row">
            <input
              aria-label="Thread ID"
              placeholder="example04-..."
              value={threadInput}
              onChange={(event) => setThreadInput(event.target.value)}
              disabled={isStreaming}
            />
            <button type="button" className="secondary" onClick={handleLoad} disabled={isStreaming}>
              Load state
            </button>
          </div>
          {threadId && (
            <div className="thread-id">
              <span>Thread ID</span>
              <code>{threadId}</code>
            </div>
          )}
          {runStatus && (
            <dl className="status-grid">
              <div>
                <dt>Status</dt>
                <dd>{runStatus.status}</dd>
              </div>
              <div>
                <dt>Decision</dt>
                <dd>{runStatus.approval_decision ?? "Pending"}</dd>
              </div>
            </dl>
          )}
        </div>

        <div className="panel activity-panel">
          <p className="section-label">Event timeline</p>
            <h2>Procurement activity</h2>
          {events.length === 0 ? (
            <p className="empty-state">Start or load a workflow to see its state transition events.</p>
          ) : (
            <ol className="event-list">
              {events.map((workflowEvent, index) => (
                <li key={`${workflowEvent.name}-${index}`}>
                  <strong>{workflowEvent.name.replaceAll("_", " ")}</strong>
                  <span>{workflowEvent.summary}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </section>

      {approvalRequired && (
        <section className="approval-card">
          <div>
            <p className="section-label">Human-in-the-loop</p>
            <h2>Approval required</h2>
            <p>{draft ?? "The persisted purchase order is waiting for a decision."}</p>
          </div>
          <div className="decision-controls">
            <button
              type="button"
              className="reject"
              onClick={() => handleDecision("reject")}
              disabled={isStreaming}
            >
              Reject
            </button>
            <button
              type="button"
              onClick={() => handleDecision("approve")}
              disabled={isStreaming}
            >
              Approve
            </button>
          </div>
        </section>
      )}

      {error && <p className="error" role="alert">{error}</p>}

      <footer>
        <span>UI boundary</span>
        Next.js ↔ FastAPI HTTP/SSE ↔ durable procurement backend
      </footer>
    </main>
  );
}
