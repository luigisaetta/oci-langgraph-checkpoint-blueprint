/** Types exchanged exclusively with the Example 04 HTTP API. */

export type Decision = "approve" | "reject";

export interface RunStatus {
  thread_id: string;
  status: string;
  draft: string | null;
  products: Array<Record<string, string | number>>;
  approval_decision: Decision | null;
  approval_required: boolean;
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
    (typeof candidate.draft === "string" || candidate.draft === null) &&
    Array.isArray(candidate.products) &&
    (candidate.approval_decision === "approve" ||
      candidate.approval_decision === "reject" ||
      candidate.approval_decision === null) &&
    typeof candidate.approval_required === "boolean"
  );
}
