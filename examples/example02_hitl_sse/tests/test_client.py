"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Tests formatting, argument parsing, and user input handling for the Example 02 client.
"""

import asyncio

import pytest

from examples.example02_hitl_sse.client import (
    DEFAULT_API_URL,
    format_client_header,
    format_workflow_timeline_event,
    iter_sse_events,
    parse_arguments,
    prompt_for_decision,
)
from utils.adb_connection import ADBConnectionConfig


def test_client_header_displays_only_safe_connection_details() -> None:
    """The client header identifies the target without exposing passwords."""
    config = ADBConnectionConfig(
        user="demo_user",
        password="database-password",
        wallet_directory="/safe/local/wallet",
        wallet_password="wallet-password",
        dsn="demo_low",
    )

    header = format_client_header("http://127.0.0.1:8080", config)

    assert "Human-in-the-Loop Agent with FastAPI SSE" in header
    assert "API URL: http://127.0.0.1:8080" in header
    assert "DB_USER: demo_user" in header
    assert "DB_DSN: demo_low" in header
    assert "WALLET_DIR: /safe/local/wallet" in header
    assert "database-password" not in header
    assert "wallet-password" not in header


def test_client_defaults_to_the_example_server_port() -> None:
    """The client targets the documented local Example 02 API endpoint."""
    assert DEFAULT_API_URL == "http://127.0.0.1:8080"


def test_sse_event_iterator_parses_named_json_events() -> None:
    """The client decodes complete SSE events from streamed response lines."""

    class FakeResponse:  # pylint: disable=too-few-public-methods
        """Supplies a minimal asynchronous SSE response."""

        async def aiter_lines(self):
            """Yield one named SSE event with a blank terminator."""
            for line in ("event: run_started", 'data: {"thread_id": "thread-1"}', ""):
                yield line

    async def collect_events() -> list[tuple[str, dict[str, object]]]:
        """Collect parsed events from the fake response."""
        return [event async for event in iter_sse_events(FakeResponse())]

    assert asyncio.run(collect_events()) == [
        ("run_started", {"thread_id": "thread-1"}),
    ]


def test_client_parses_default_api_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """The command-line client defaults to the documented Example 02 URL."""
    monkeypatch.setattr("sys.argv", ["client.py", "Prepare report"])

    arguments = parse_arguments()

    assert arguments.message == "Prepare report"
    assert arguments.api_url == "http://127.0.0.1:8080"


def test_decision_prompt_retries_until_input_is_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The interactive prompt rejects unsupported approval decisions."""
    decisions = iter(("later", "approve"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(decisions))

    assert prompt_for_decision() == "approve"


@pytest.mark.parametrize(
    ("event_name", "payload", "expected"),
    [
        (
            "node_update",
            {"node": "intake", "update": {}},
            "[1/3] Intake completed | Request accepted and normalized.",
        ),
        (
            "node_update",
            {"node": "draft", "update": {}},
            "[2/3] Draft completed | Draft is ready for human review.",
        ),
        (
            "approval_required",
            {},
            "[3/3] Waiting for your approval | Review the draft below.",
        ),
        (
            "node_update",
            {"node": "approval", "update": {"approval_decision": "approve"}},
            "[3/3] Approval completed | Decision recorded: approve.",
        ),
        (
            "run_completed",
            {"state": {"status": "approved"}},
            "[Workflow] Completed | Final status: approved.",
        ),
    ],
)
def test_workflow_timeline_describes_agent_progress(
    event_name: str,
    payload: dict[str, object],
    expected: str,
) -> None:
    """The client presents a readable timeline alongside raw SSE event data."""
    assert format_workflow_timeline_event(event_name, payload) == expected


def test_workflow_timeline_ignores_unknown_events() -> None:
    """Events outside the client contract do not add a misleading timeline line."""
    assert format_workflow_timeline_event("unknown", {}) is None
