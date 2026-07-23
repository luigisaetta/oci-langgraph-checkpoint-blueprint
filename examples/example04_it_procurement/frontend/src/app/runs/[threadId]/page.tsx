"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { getRunStatus, WorkflowApiError } from "../../../lib/api";
import type { RunStatus } from "../../../lib/types";

const API_URL =
  process.env.NEXT_PUBLIC_EXAMPLE04_API_URL ?? "http://127.0.0.1:8082";

function errorMessage(error: unknown): string {
  if (error instanceof WorkflowApiError || error instanceof Error) {
    return error.message;
  }
  return "The process details could not be loaded.";
}

function lifecycleLabel(status: string): string {
  return status.replaceAll("_", " ").replace(/\b\w/g, (character) =>
    character.toUpperCase(),
  );
}

function valueOrUnavailable(value: string | number | null): string | number {
  return value ?? "Not available";
}

export default function ProcessDetailPage() {
  const params = useParams<{ threadId: string }>();
  const threadId = params.threadId;
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRunStatus(): Promise<void> {
      setIsLoading(true);
      setError(null);
      try {
        setRunStatus(await getRunStatus(API_URL, threadId));
      } catch (caughtError) {
        setError(errorMessage(caughtError));
      } finally {
        setIsLoading(false);
      }
    }

    if (threadId) {
      void loadRunStatus();
    }
  }, [threadId]);

  return (
    <main>
      <section className="hero compact-hero">
        <nav className="page-nav" aria-label="Primary navigation">
          <Link href="/">New request</Link>
          <Link href="/runs">Process instances</Link>
        </nav>
        <p className="eyebrow">Example 04 · Durable workflows</p>
        <h1>Process details</h1>
        <p className="hero-copy">
          The information below is reconstructed from the durable workflow
          state held by the Example 04 backend.
        </p>
      </section>

      <section className="panel detail-panel" aria-labelledby="process-details-heading">
        <p className="section-label">Durable state</p>
        <h2 id="process-details-heading">Procurement process</h2>
        {isLoading && <p className="empty-state">Loading process details…</p>}
        {!isLoading && error && <p className="error" role="alert">{error}</p>}
        {!isLoading && runStatus && (
          <dl className="detail-grid">
            <div className="detail-item full-width">
              <dt>Process ID</dt>
              <dd><code>{runStatus.thread_id}</code></dd>
            </div>
            <div className="detail-item">
              <dt>Current status</dt>
              <dd>{lifecycleLabel(runStatus.status)}</dd>
            </div>
            <div className="detail-item">
              <dt>Approval decision</dt>
              <dd>{valueOrUnavailable(runStatus.approval_decision)}</dd>
            </div>
            <div className="detail-item full-width">
              <dt>Original request</dt>
              <dd>{valueOrUnavailable(runStatus.message)}</dd>
            </div>
            <div className="detail-item">
              <dt>Requested item</dt>
              <dd>{valueOrUnavailable(runStatus.requested_object)}</dd>
            </div>
            <div className="detail-item">
              <dt>Quantity</dt>
              <dd>{valueOrUnavailable(runStatus.quantity)}</dd>
            </div>
            <div className="detail-item full-width">
              <dt>Simulated offer</dt>
              <dd>{valueOrUnavailable(runStatus.draft)}</dd>
            </div>
          </dl>
        )}
      </section>
    </main>
  );
}
