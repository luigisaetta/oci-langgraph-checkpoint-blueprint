"""
Author: L. Saetta
Date last modified: 2026-07-22
License: MIT
Description: Tests the Example 03 recovery-client command-line interface.
"""

import asyncio
import json
from typing import Any

import pytest

from examples.example03_production_hitl import client as example_client
from examples.example03_production_hitl.client import (
    DEFAULT_API_URL,
    iter_sse_events,
    parse_arguments,
)


def test_client_parses_the_three_recovery_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI accepts independent start, status, and decide operations."""
    monkeypatch.setattr("sys.argv", ["client.py", "start", "Review report"])
    start_arguments = parse_arguments()

    monkeypatch.setattr("sys.argv", ["client.py", "status", "example03-123"])
    status_arguments = parse_arguments()

    monkeypatch.setattr(
        "sys.argv",
        ["client.py", "--api-url", "http://api", "decide", "example03-123", "approve"],
    )
    decide_arguments = parse_arguments()

    assert DEFAULT_API_URL == "http://127.0.0.1:8081"
    assert (start_arguments.command, start_arguments.message) == (
        "start",
        "Review report",
    )
    assert (status_arguments.command, status_arguments.thread_id) == (
        "status",
        "example03-123",
    )
    assert (decide_arguments.api_url, decide_arguments.decision) == (
        "http://api",
        "approve",
    )


def test_client_parses_sse_and_guides_a_restart(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The start command stops at approval and prints the next recovery action."""

    class FakeResponse:  # pylint: disable=too-few-public-methods
        """Supplies one complete named SSE event."""

        async def aiter_lines(self):
            """Yield the lines of one named event."""
            for line in ("event: run_started", 'data: {"thread_id": "thread-1"}', ""):
                yield line

    async def collect_events() -> list[tuple[str, dict[str, Any]]]:
        """Collect parsed SSE events from the fake response."""
        return [event async for event in iter_sse_events(FakeResponse())]

    async def fake_consume(*_args: Any) -> tuple[str, bool]:
        """Return a paused workflow without an HTTP call."""
        return "example03-restart", True

    monkeypatch.setattr(example_client, "consume_stream", fake_consume)
    asyncio.run(example_client.start_run("http://api", "Review report"))

    assert asyncio.run(collect_events()) == [("run_started", {"thread_id": "thread-1"})]
    output = capsys.readouterr().out
    assert "Workflow paused and persisted in ADB." in output
    assert "client status example03-restart" in output


def test_client_status_and_decision_use_the_http_api(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Status uses GET while decision reuses the stream consumer."""
    requested_urls: list[str] = []

    class FakeResponse:
        """Supplies a successful JSON status response."""

        def raise_for_status(self) -> None:
            """Accept the fake response."""

        def json(self) -> dict[str, str]:
            """Return the persisted status payload."""
            return {"status": "awaiting_approval"}

    class FakeClient:
        """Supplies the subset of AsyncClient used by status."""

        async def __aenter__(self) -> "FakeClient":
            """Enter the fake client context."""
            return self

        async def __aexit__(self, *_args: Any) -> None:
            """Exit the fake client context."""

        async def get(self, url: str) -> FakeResponse:
            """Record and answer a status request."""
            requested_urls.append(url)
            return FakeResponse()

    async def fake_consume(
        _client: Any, url: str, payload: dict[str, str]
    ) -> tuple[None, bool]:
        """Record a decision request without opening a stream."""
        requested_urls.append(f"{url}:{json.dumps(payload, sort_keys=True)}")
        return None, False

    monkeypatch.setattr(
        example_client.httpx, "AsyncClient", lambda *args, **kwargs: FakeClient()
    )
    monkeypatch.setattr(example_client, "consume_stream", fake_consume)

    asyncio.run(example_client.show_status("http://api", "thread-1"))
    asyncio.run(example_client.submit_decision("http://api", "thread-1", "approve"))

    assert requested_urls == [
        "http://api/runs/thread-1",
        'http://api/runs/thread-1/decision:{"decision": "approve"}',
    ]
    assert '"awaiting_approval"' in capsys.readouterr().out
