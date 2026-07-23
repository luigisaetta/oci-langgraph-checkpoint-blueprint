"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getRunSummaries, WorkflowApiError } from "../../lib/api";
import type { RunSummary } from "../../lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_EXAMPLE04_API_URL ?? "http://127.0.0.1:8082";

function errorMessage(error: unknown): string {
  if (error instanceof WorkflowApiError || error instanceof Error) {
    return error.message;
  }
  return "The process-instance list could not be loaded.";
}

function statusLabel(status: RunSummary["status"]): string {
  return status === "completed" ? "Completed" : "In progress";
}

function submittedAtLabel(submittedAt: string): string {
  const timestamp = new Date(submittedAt);
  if (Number.isNaN(timestamp.getTime())) {
    return submittedAt;
  }
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(timestamp);
}

export default function ProcessInstancesPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedThreadId, setCopiedThreadId] = useState<string | null>(null);

  async function loadRuns(): Promise<void> {
    setIsLoading(true);
    setError(null);
    try {
      setRuns(await getRunSummaries(API_URL));
    } catch (caughtError) {
      setError(errorMessage(caughtError));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadRuns();
  }, []);

  async function copyProcessId(threadId: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(threadId);
      setCopiedThreadId(threadId);
    } catch {
      setError("The process ID could not be copied. Select and copy it manually.");
    }
  }

  return (
    <main>
      <section className="hero compact-hero">
        <nav className="page-nav" aria-label="Primary navigation">
          <Link href="/">New request</Link>
          <Link href="/runs" aria-current="page">Process instances</Link>
        </nav>
        <p className="eyebrow">Example 04 · Durable workflows</p>
        <h1>Process instances</h1>
        <p className="hero-copy">
          Every row is reconstructed from the Oracle ADB checkpoints through
          the Example 04 backend.
        </p>
      </section>

      <section className="panel instance-panel" aria-labelledby="instances-heading">
        <div className="workflow-heading">
          <div>
            <p className="section-label">Durable state</p>
            <h2 id="instances-heading">Known procurement processes</h2>
          </div>
          <button type="button" className="secondary" onClick={() => void loadRuns()} disabled={isLoading}>
            Refresh
          </button>
        </div>

        {isLoading && <p className="empty-state">Loading process instances…</p>}
        {!isLoading && error && <p className="error" role="alert">{error}</p>}
        {!isLoading && !error && runs.length === 0 && (
          <p className="empty-state">No procurement processes have been persisted yet.</p>
        )}
        {!isLoading && !error && runs.length > 0 && (
          <div className="instance-table-wrap">
            <table className="instance-table">
              <thead>
                <tr><th scope="col">Process ID</th><th scope="col">Submitted at</th><th scope="col">Current status</th></tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.thread_id}>
                    <td>
                      <div className="process-id-cell">
                        <Link href={`/runs/${encodeURIComponent(run.thread_id)}`}>
                          <code>{run.thread_id}</code>
                        </Link>
                        <button
                          type="button"
                          className="copy-button"
                          onClick={() => void copyProcessId(run.thread_id)}
                        >
                          {copiedThreadId === run.thread_id ? "Copied" : "Copy ID"}
                        </button>
                      </div>
                    </td>
                    <td>{submittedAtLabel(run.submitted_at)}</td>
                    <td><span className={`instance-status ${run.status}`}>{statusLabel(run.status)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
