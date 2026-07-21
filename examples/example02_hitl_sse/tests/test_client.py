"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Tests the safe presentation header of the Example 02 Python client.
"""

import pytest

from examples.example02_hitl_sse.client import (
    format_client_header,
    format_workflow_timeline_event,
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

    header = format_client_header("http://127.0.0.1:8000", config)

    assert "Human-in-the-Loop Agent with FastAPI SSE" in header
    assert "API URL: http://127.0.0.1:8000" in header
    assert "DB_USER: demo_user" in header
    assert "DB_DSN: demo_low" in header
    assert "WALLET_DIR: /safe/local/wallet" in header
    assert "database-password" not in header
    assert "wallet-password" not in header


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
