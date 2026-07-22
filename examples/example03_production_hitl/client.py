"""
Author: L. Saetta
Date last modified: 2026-07-22
License: MIT
Description: Provides start, status, and decide commands for Example 03 recovery demos.
"""

import argparse
import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

DEFAULT_API_URL = "http://127.0.0.1:8081"


async def iter_sse_events(
    response: httpx.Response,
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Parse named JSON SSE events from an open HTTP response.

    Args:
        response: Open streaming HTTP response.

    Yields:
        Pairs containing an event name and decoded JSON payload.
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
    url: str,
    payload: dict[str, str],
) -> tuple[str | None, bool]:
    """Display an SSE response and return its thread ID and pause state.

    Args:
        client: HTTP client used for the streaming request.
        url: Full endpoint URL.
        payload: JSON request body.

    Returns:
        The observed thread ID and whether the graph paused for approval.

    Raises:
        httpx.HTTPStatusError: If the service rejects the request.
    """
    thread_id: str | None = None
    approval_required = False
    async with client.stream("POST", url, json=payload) as response:
        response.raise_for_status()
        async for event_name, event_payload in iter_sse_events(response):
            print(f"[{event_name}] {json.dumps(event_payload, indent=2)}")
            print()
            thread_id = event_payload.get("thread_id", thread_id)
            approval_required = approval_required or event_name == "approval_required"
    return thread_id, approval_required


async def start_run(api_url: str, message: str) -> None:
    """Start a workflow, display its pause information, and exit.

    Args:
        api_url: Base URL of the Example 03 service.
        message: Initial workflow message.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        thread_id, approval_required = await consume_stream(
            client,
            f"{api_url}/runs",
            {"message": message},
        )
    if approval_required and thread_id is not None:
        print("Workflow paused and persisted in ADB.")
        print(f"Thread ID: {thread_id}")
        print("You can now restart the FastAPI server to simulate a deployment.")
        print("After restart, inspect the persisted state with:")
        print(f"  client status {thread_id}")


async def show_status(api_url: str, thread_id: str) -> None:
    """Retrieve and display the persisted state of one workflow.

    Args:
        api_url: Base URL of the Example 03 service.
        thread_id: Durable workflow identifier.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_url}/runs/{thread_id}")
        response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


async def submit_decision(api_url: str, thread_id: str, decision: str) -> None:
    """Resume a persisted workflow and display its final SSE events.

    Args:
        api_url: Base URL of the Example 03 service.
        thread_id: Durable workflow identifier.
        decision: ``approve`` or ``reject``.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        await consume_stream(
            client,
            f"{api_url}/runs/{thread_id}/decision",
            {"decision": decision},
        )


def parse_arguments() -> argparse.Namespace:
    """Parse Example 03 client commands and their arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Example 03 recovery demo client")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="FastAPI base URL")
    commands = parser.add_subparsers(dest="command", required=True)

    start_parser = commands.add_parser(
        "start", help="Start a workflow and stop at approval"
    )
    start_parser.add_argument("message", help="Message processed by the workflow")

    status_parser = commands.add_parser(
        "status", help="Read a persisted workflow state"
    )
    status_parser.add_argument("thread_id", help="Persistent workflow thread ID")

    decide_parser = commands.add_parser("decide", help="Resume a paused workflow")
    decide_parser.add_argument("thread_id", help="Persistent workflow thread ID")
    decide_parser.add_argument("decision", choices=("approve", "reject"))
    return parser.parse_args()


def main() -> None:
    """Run the selected Example 03 client command."""
    arguments = parse_arguments()
    api_url = arguments.api_url.rstrip("/")
    if arguments.command == "start":
        asyncio.run(start_run(api_url, arguments.message))
    elif arguments.command == "status":
        asyncio.run(show_status(api_url, arguments.thread_id))
    else:
        asyncio.run(submit_decision(api_url, arguments.thread_id, arguments.decision))


if __name__ == "__main__":
    main()
