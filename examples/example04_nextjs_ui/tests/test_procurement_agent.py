"""
Author: L. Saetta
Date last modified: 2026-07-23
License: MIT
Description: Tests the deterministic IT procurement graph and HTTP API boundary.
"""

from collections.abc import Iterator
import importlib
from typing import Any

from fastapi.testclient import TestClient

from examples.example02_hitl_sse.streaming import format_sse
from examples.example04_nextjs_ui.app import (
    RunStatus,
    generate_thread_id,
    read_run_status,
    stream_run,
)
from examples.example04_nextjs_ui.procurement_graph import (
    create_order_proposal,
    intake_request,
)


def test_order_proposal_matches_catalogue_and_quantity() -> None:
    """A mouse request produces a deterministic two-unit order proposal."""
    intake = intake_request({"message": "Order 2 wireless mice"})
    proposal = create_order_proposal(intake)

    assert intake["quantity"] == 2
    assert proposal["products"][0]["sku"] == "MOU-100"
    assert "EUR 58" in proposal["draft"]
    assert proposal["status"] == "awaiting_approval"


def test_order_proposal_explains_a_catalogue_miss() -> None:
    """An unsupported product request has a safe, actionable proposal."""
    intake = intake_request({"message": "Order a projector"})
    proposal = create_order_proposal(intake)

    assert proposal["products"] == []
    assert proposal["draft"].startswith("No catalogue products matched")


def test_intake_defaults_quantity_and_catalogue_supports_italian_terms() -> None:
    """The deterministic catalogue accepts a default quantity and Italian terms."""
    intake = intake_request({"message": "Mi serve una tastiera"})
    proposal = create_order_proposal(intake)

    assert intake["quantity"] == 1
    assert proposal["products"][0]["sku"] == "KEY-200"


def test_status_reader_and_streamer_use_the_example04_graph(
    monkeypatch: Any,
) -> None:
    """State reconstruction and streaming use the local procurement graph."""
    application_module = importlib.import_module("examples.example04_nextjs_ui.app")

    class FakeSnapshot:  # pylint: disable=too-few-public-methods
        """Provides a deterministic persisted state."""

        values = {
            "status": "awaiting_approval",
            "draft": "Draft",
            "products": [{"sku": "MOU-100"}],
        }

    class FakeGraph:  # pylint: disable=too-few-public-methods
        """Provides graph operations used by the application boundary."""

        def get_state(self, _config: dict[str, Any]) -> FakeSnapshot:
            """Return the persisted state."""
            return FakeSnapshot()

    monkeypatch.setattr(application_module, "OracleSaver", lambda _pool: object())
    monkeypatch.setattr(
        application_module, "build_procurement_graph", lambda _saver: FakeGraph()
    )
    monkeypatch.setattr(
        application_module,
        "stream_graph_updates",
        lambda *_args: iter([format_sse("run_completed", {"thread_id": "thread"})]),
    )

    run_status = read_run_status(object(), "thread")
    events = list(stream_run(object(), "thread", {"message": "mouse"}, False))

    assert run_status is not None
    assert run_status.approval_required is True
    assert run_status.products == [{"sku": "MOU-100"}]
    assert events[0].startswith("event: run_completed")


def test_api_resumes_once_and_acknowledges_repeated_decision() -> None:
    """A repeated final decision returns completion without graph execution."""
    streamer_calls: list[str] = []
    statuses = {
        "paused": RunStatus(
            thread_id="paused",
            status="awaiting_approval",
            draft="Simulated purchase order",
            products=[],
            approval_required=True,
        ),
        "ordered": RunStatus(
            thread_id="ordered",
            status="ordered",
            draft="Simulated purchase order",
            products=[],
            approval_decision="approve",
            approval_required=False,
        ),
    }

    def streamer(
        _pool: Any, thread_id: str, _graph_input: Any, _is_resume: bool
    ) -> Iterator[str]:
        streamer_calls.append(thread_id)
        yield format_sse("run_completed", {"thread_id": thread_id, "state": {}})

    application = importlib.import_module(
        "examples.example04_nextjs_ui.app"
    ).create_app(
        streamer=streamer,
        status_reader=lambda _pool, thread_id: statuses.get(thread_id),
        initialize_database=False,
    )
    application.state.adb_pool = object()
    with TestClient(application) as client:
        assert client.get("/runs/paused").json()["approval_required"] is True
        assert (
            client.post(
                "/runs/paused/decision", json={"decision": "approve"}
            ).status_code
            == 200
        )
        repeated = client.post("/runs/ordered/decision", json={"decision": "approve"})
        conflicting = client.post("/runs/ordered/decision", json={"decision": "reject"})

    assert streamer_calls == ["paused"]
    assert '"idempotent": true' in repeated.text
    assert conflicting.status_code == 409


def test_api_reports_missing_run_and_start_uses_example04_prefix() -> None:
    """The API handles an unknown run and keeps its durable threads isolated."""
    application = importlib.import_module(
        "examples.example04_nextjs_ui.app"
    ).create_app(
        streamer=lambda *_args: iter(()),
        status_reader=lambda _pool, _thread_id: None,
        initialize_database=False,
    )
    application.state.adb_pool = object()
    with TestClient(application) as client:
        assert client.get("/runs/missing").status_code == 404
        response = client.post("/runs", json={"message": "Order a mouse"})

    assert response.status_code == 200
    assert generate_thread_id().startswith("example04-")
