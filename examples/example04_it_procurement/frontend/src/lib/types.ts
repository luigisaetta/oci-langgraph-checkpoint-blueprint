/** Types exchanged exclusively with the Example 04 HTTP API. */

export type Decision = "approve" | "reject";

export interface RunStatus {
  thread_id: string;
  status: string;
  message: string | null;
  draft: string | null;
  requested_object: string | null;
  quantity: number | null;
  approval_decision: Decision | null;
  approval_required: boolean;
}

export interface RunSummary {
  thread_id: string;
  status: "in_progress" | "completed";
  submitted_at: string;
}

export type WorkflowEventName =
  | "run_started"
  | "node_update"
  | "approval_required"
  | "run_completed"
  | "error";

export interface WorkflowEvent {
  name: WorkflowEventName | string;
  payload: Record<string, unknown>;
}

export type FetchImplementation = typeof fetch;

export function isRunStatus(value: unknown): value is RunStatus {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.thread_id === "string" &&
    typeof candidate.status === "string" &&
    (typeof candidate.message === "string" || candidate.message === null) &&
    (typeof candidate.draft === "string" || candidate.draft === null) &&
    (typeof candidate.requested_object === "string" ||
      candidate.requested_object === null) &&
    (typeof candidate.quantity === "number" || candidate.quantity === null) &&
    (candidate.approval_decision === "approve" ||
      candidate.approval_decision === "reject" ||
      candidate.approval_decision === null) &&
    typeof candidate.approval_required === "boolean"
  );
}

export function isRunSummaryList(value: unknown): value is RunSummary[] {
  return Array.isArray(value) && value.every((candidate) => {
    if (!candidate || typeof candidate !== "object") {
      return false;
    }
    const summary = candidate as Record<string, unknown>;
    return (
      typeof summary.thread_id === "string" &&
      (summary.status === "in_progress" || summary.status === "completed") &&
      typeof summary.submitted_at === "string"
    );
  });
}
