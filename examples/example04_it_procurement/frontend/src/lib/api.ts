import { consumeSseResponse } from "./sse";
import type {
  Decision,
  FetchImplementation,
  RunStatus,
  WorkflowEvent,
} from "./types";
import { isRunStatus } from "./types";

/** Represents a safe, user-displayable Example 04 API failure. */
export class WorkflowApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "WorkflowApiError";
  }
}

function endpoint(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

async function messageForFailedResponse(response: Response): Promise<string> {
  let detail = "";
  try {
    const payload: unknown = await response.json();
    if (payload && typeof payload === "object" && "detail" in payload) {
      detail = String(payload.detail);
    }
  } catch {
    // A non-JSON error body is safe to replace with a generic message.
  }
  return detail || `The workflow service returned HTTP ${response.status}.`;
}

async function requireSuccessfulResponse(response: Response): Promise<void> {
  if (!response.ok) {
    throw new WorkflowApiError(
      await messageForFailedResponse(response),
      response.status,
    );
  }
}

/** Retrieve the persisted state of one durable Example 04 procurement run. */
export async function getRunStatus(
  apiUrl: string,
  threadId: string,
  fetcher: FetchImplementation = fetch,
): Promise<RunStatus> {
  const response = await fetcher(
    endpoint(apiUrl, `/runs/${encodeURIComponent(threadId)}`),
  );
  await requireSuccessfulResponse(response);
  const payload: unknown = await response.json();
  if (!isRunStatus(payload)) {
    throw new WorkflowApiError("The workflow service returned an invalid status.");
  }
  return payload;
}

async function streamWorkflow(
  apiUrl: string,
  path: string,
  body: Record<string, string>,
  onEvent: (event: WorkflowEvent) => void,
  fetcher: FetchImplementation = fetch,
): Promise<void> {
  let response: Response;
  try {
    response = await fetcher(endpoint(apiUrl, path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new WorkflowApiError(
      "Cannot reach the procurement service. Confirm that Example 04 is running.",
    );
  }
  await requireSuccessfulResponse(response);
  await consumeSseResponse(response, onEvent);
}

/** Start a new durable workflow and deliver every named SSE event. */
export async function startRun(
  apiUrl: string,
  message: string,
  onEvent: (event: WorkflowEvent) => void,
  fetcher: FetchImplementation = fetch,
): Promise<void> {
  return streamWorkflow(apiUrl, "/runs", { message }, onEvent, fetcher);
}

/** Resume a paused durable workflow with a human decision. */
export async function submitDecision(
  apiUrl: string,
  threadId: string,
  decision: Decision,
  onEvent: (event: WorkflowEvent) => void,
  fetcher: FetchImplementation = fetch,
): Promise<void> {
  return streamWorkflow(
    apiUrl,
    `/runs/${encodeURIComponent(threadId)}/decision`,
    { decision },
    onEvent,
    fetcher,
  );
}
