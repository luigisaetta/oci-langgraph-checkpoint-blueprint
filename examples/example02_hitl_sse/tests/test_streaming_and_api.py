"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Tests SSE formatting, stream translation, and FastAPI request validation.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

from fastapi.testclient import TestClient
from langgraph.types import Command

from examples.example02_hitl_sse import app as example_app
from examples.example02_hitl_sse.app import create_app
from examples.example02_hitl_sse.streaming import format_sse, stream_graph_updates


@dataclass
class FakeSnapshot:
    """Provides the final state expected by the SSE stream adapter."""

    values: dict[str, str]


class FakeGraph:
    """Supplies deterministic LangGraph v2-style stream chunks for tests."""

    def stream(self, *_args: Any, **_kwargs: Any) -> Iterator[dict[str, Any]]:
        """Yield one node update followed by one human interrupt.

        Yields:
            LangGraph v2-style update chunks.
        """
        yield {"type": "updates", "data": {"intake": {"status": "drafting"}}}
        yield {
            "type": "updates",
            "data": {
                "__interrupt__": (
                    type("Interrupt", (), {"value": {"question": "Approve?"}})(),
                )
            },
        }

    def get_state(self, _config: dict[str, Any]) -> FakeSnapshot:
        """Return a deterministic completed-state snapshot.

        Args:
            config: Graph configuration supplied by the stream adapter.

        Returns:
            A fake final snapshot.
        """
        return FakeSnapshot(values={"status": "approved"})


def test_format_sse_uses_named_json_events() -> None:
    """SSE messages contain an event name, JSON payload, and blank terminator."""
    event = format_sse("node_update", {"node": "intake"})

    assert event == 'event: node_update\ndata: {"node": "intake"}\n\n'


def test_stream_adapter_emits_node_update_and_approval_request() -> None:
    """LangGraph updates and interrupts are translated to named SSE events."""
    events = list(
        stream_graph_updates(
            FakeGraph(),
            {"message": "hello"},
            "example02-test",
        )
    )

    assert events[0].startswith("event: run_started")
    assert events[1].startswith("event: node_update")
    assert events[2].startswith("event: approval_required")
    assert not any(event.startswith("event: run_completed") for event in events)


def test_api_validates_start_and_decision_requests_without_database() -> None:
    """The FastAPI boundary validates payloads before calling a graph streamer."""
    calls: list[tuple[str, Any, bool]] = []

    def streamer(thread_id: str, graph_input: Any, is_resume: bool) -> Iterator[str]:
        calls.append((thread_id, graph_input, is_resume))
        yield format_sse("run_started", {"thread_id": thread_id})

    application = create_app(streamer=streamer, initialize_database=False)
    with TestClient(application) as client:
        invalid_start = client.post("/runs", json={"message": "   "})
        valid_start = client.post("/runs", json={"message": "review report"})
        thread_id = calls[0][0]
        invalid_decision = client.post(
            f"/runs/{thread_id}/decision",
            json={"decision": "maybe"},
        )
        valid_decision = client.post(
            f"/runs/{thread_id}/decision",
            json={"decision": "approve"},
        )

    assert invalid_start.status_code == 422
    assert valid_start.status_code == 200
    assert invalid_decision.status_code == 422
    assert valid_decision.status_code == 200
    assert calls[0][0].startswith("example02-")
    assert calls[0][2] is False
    assert isinstance(calls[1][1], Command)
    assert calls[1][2] is True


def test_main_runs_uvicorn_on_the_default_example_port(
    monkeypatch: Any,
) -> None:
    """The module entry point keeps the documented local port as its default."""
    run_server = Mock()
    monkeypatch.setattr(example_app.uvicorn, "run", run_server)

    example_app.main()

    run_server.assert_called_once_with(
        "examples.example02_hitl_sse.app:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
    )
