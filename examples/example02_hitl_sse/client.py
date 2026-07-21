"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Streams Example 02 SSE events and submits a human approval decision.
"""

import argparse
import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

DEFAULT_API_URL = "http://127.0.0.1:8000"


async def iter_sse_events(
    response: httpx.Response,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Parse named SSE events from an HTTPX streaming response.

    Args:
        response: Open HTTPX response with an SSE body.

    Yields:
        Pairs containing the event name and decoded JSON payload.
    """
    event_name = "message"
    data_lines: list[str] = []
    async for line in response.aiter_lines():
        if not line:
            if data_lines:
                yield event_name, json.loads("\n".join(data_lines))
            event_name = "message"
            data_lines = []
        elif line.startswith("event:"):
            event_name = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())


async def consume_stream(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    payload: dict[str, str],
) -> tuple[str | None, bool]:
    """Display an SSE stream and return its thread and approval state.

    Args:
        client: HTTP client used to connect to the FastAPI server.
        method: HTTP method for the stream request.
        url: Full API endpoint URL.
        payload: JSON body sent to the endpoint.

    Returns:
        The thread ID seen in the stream and whether approval is required.

    Raises:
        httpx.HTTPStatusError: If the server rejects the request.
    """
    thread_id: str | None = None
    approval_required = False
    async with client.stream(method, url, json=payload) as response:
        response.raise_for_status()
        async for event_name, event_payload in iter_sse_events(response):
            print(f"[{event_name}] {json.dumps(event_payload, indent=2)}")
            thread_id = event_payload.get("thread_id", thread_id)
            if event_name == "approval_required":
                approval_required = True
            if event_name == "error":
                approval_required = False
    return thread_id, approval_required


def prompt_for_decision() -> str:
    """Prompt until the user supplies a valid HITL decision.

    Returns:
        Either ``approve`` or ``reject``.
    """
    while True:
        decision = input("Decision [approve/reject]: ").strip().lower()
        if decision in {"approve", "reject"}:
            return decision
        print("Please enter exactly 'approve' or 'reject'.")


async def run_client(api_url: str, message: str) -> None:
    """Start an agent run, gather human input, and resume the same thread.

    Args:
        api_url: Base URL of the Example 02 FastAPI service.
        message: Initial agent message.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        thread_id, approval_required = await consume_stream(
            client,
            "POST",
            f"{api_url}/runs",
            {"message": message},
        )
        if not approval_required:
            return
        if thread_id is None:
            raise RuntimeError("The approval stream did not include a thread ID.")

        decision = prompt_for_decision()
        await consume_stream(
            client,
            "POST",
            f"{api_url}/runs/{thread_id}/decision",
            {"decision": decision},
        )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options for the Example 02 client.

    Returns:
        Parsed client command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Example 02 HITL SSE client")
    parser.add_argument("message", help="Message processed by the agent")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="FastAPI base URL")
    return parser.parse_args()


def main() -> None:
    """Run the interactive Example 02 client."""
    arguments = parse_arguments()
    asyncio.run(run_client(arguments.api_url.rstrip("/"), arguments.message))


if __name__ == "__main__":
    main()
