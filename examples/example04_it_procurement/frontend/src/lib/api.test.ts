import { describe, expect, it, vi } from "vitest";

import { getRunStatus, getRunSummaries, startRun, WorkflowApiError } from "./api";

describe("getRunStatus", () => {
  it("returns a validated persisted run status", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      Response.json({
        thread_id: "example04-1",
        status: "awaiting_approval",
        message: "Order 2 wireless mice",
        draft: "Draft",
        requested_object: "wireless mouse",
        quantity: 2,
        approval_decision: null,
        approval_required: true,
      }),
    );

    await expect(getRunStatus("http://api.example", "example04-1", fetcher)).resolves
      .toMatchObject({ thread_id: "example04-1", approval_required: true });
  });

  it("returns a safe API error for an HTTP failure", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      Response.json({ detail: "Run not found." }, { status: 404 }),
    );

    await expect(getRunStatus("http://api.example", "missing", fetcher)).rejects.toEqual(
      new WorkflowApiError("Run not found.", 404),
    );
  });
});

describe("startRun", () => {
  it("posts the message and forwards named SSE events", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response('event: run_started\ndata: {"thread_id":"example04-1"}\n\n'),
    );
    const eventNames: string[] = [];

    await startRun("http://api.example", "Prepare report", (event) => {
      eventNames.push(event.name);
    }, fetcher);

    expect(fetcher).toHaveBeenCalledWith("http://api.example/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Prepare report" }),
    });
    expect(eventNames).toEqual(["run_started"]);
  });
});

describe("getRunSummaries", () => {
  it("returns validated process-instance summaries", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      Response.json([
        {
          thread_id: "example04-1",
          status: "in_progress",
          submitted_at: "2026-07-23T12:00:00+00:00",
        },
        {
          thread_id: "example04-2",
          status: "completed",
          submitted_at: "2026-07-23T10:00:00+00:00",
        },
      ]),
    );

    await expect(getRunSummaries("http://api.example", fetcher)).resolves.toEqual([
      {
        thread_id: "example04-1",
        status: "in_progress",
        submitted_at: "2026-07-23T12:00:00+00:00",
      },
      {
        thread_id: "example04-2",
        status: "completed",
        submitted_at: "2026-07-23T10:00:00+00:00",
      },
    ]);
  });
});
