import type { WorkflowEvent } from "./types";

/** Raised when the Example 03 stream is not valid named JSON SSE data. */
export class SseParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SseParseError";
  }
}

/** Parse one complete SSE block, excluding its blank-line delimiter. */
export function parseSseBlock(block: string): WorkflowEvent | null {
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of block.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  try {
    const payload: unknown = JSON.parse(dataLines.join("\n"));
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw new SseParseError("SSE payload must be a JSON object.");
    }
    return { name: eventName, payload: payload as Record<string, unknown> };
  } catch (error) {
    if (error instanceof SseParseError) {
      throw error;
    }
    throw new SseParseError("SSE payload is not valid JSON.");
  }
}

/** Consume a fetch response body and deliver complete named SSE events in order. */
export async function consumeSseResponse(
  response: Response,
  onEvent: (event: WorkflowEvent) => void,
): Promise<void> {
  if (!response.body) {
    throw new SseParseError("The API returned an empty event stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processAvailableBlocks = (): void => {
    let boundary = buffer.search(/\r?\n\r?\n/);
    while (boundary >= 0) {
      const delimiter = buffer.match(/\r?\n\r?\n/);
      if (!delimiter || delimiter.index === undefined) {
        return;
      }
      const event = parseSseBlock(buffer.slice(0, delimiter.index));
      buffer = buffer.slice(delimiter.index + delimiter[0].length);
      if (event) {
        onEvent(event);
      }
      boundary = buffer.search(/\r?\n\r?\n/);
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    processAvailableBlocks();
  }
  buffer += decoder.decode();
  processAvailableBlocks();
  if (buffer.trim()) {
    const event = parseSseBlock(buffer);
    if (event) {
      onEvent(event);
    }
  }
}
