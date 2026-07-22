import { describe, expect, it } from "vitest";

import { consumeSseResponse, parseSseBlock, SseParseError } from "./sse";

describe("parseSseBlock", () => {
  it("parses a named JSON event", () => {
    expect(
      parseSseBlock('event: approval_required\ndata: {"thread_id":"thread-1"}'),
    ).toEqual({
      name: "approval_required",
      payload: { thread_id: "thread-1" },
    });
  });

  it("rejects malformed JSON payloads", () => {
    expect(() => parseSseBlock("event: error\ndata: not-json")).toThrow(
      SseParseError,
    );
  });
});

describe("consumeSseResponse", () => {
  it("joins fragmented response chunks into ordered events", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('event: run_started\ndata: {"thread'));
        controller.enqueue(encoder.encode('_id":"thread-1"}\n\nevent: run_completed\ndata: {}\n\n'));
        controller.close();
      },
    });
    const events: string[] = [];

    await consumeSseResponse(new Response(stream), (event) => {
      events.push(event.name);
    });

    expect(events).toEqual(["run_started", "run_completed"]);
  });
});
