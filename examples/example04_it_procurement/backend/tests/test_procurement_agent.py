"""
Author: L. Saetta
Date last modified: 2026-07-23
License: MIT
Description: Tests the OCI LLM procurement graph and HTTP API boundary without OCI.
"""

from collections.abc import Iterator
import importlib
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
import pytest

from examples.example02_hitl_sse.streaming import format_sse
from examples.example04_it_procurement.backend.app import (
    RunStatus,
    generate_thread_id,
    read_run_summaries,
    read_run_status,
    stream_run,
)
from examples.example04_it_procurement.backend.llm_factory import (
    build_oci_openai_base_url,
)
from examples.example04_it_procurement.backend.procurement_graph import (
    IntakeNode,
    OfferNode,
)
from examples.example04_it_procurement.backend.procurement_llm import (
    ProcurementInferenceError,
    ProcurementLlmService,
)


class FakeResponses:  # pylint: disable=too-few-public-methods
    """Records Responses API arguments and returns configured text outputs."""

    def __init__(self, outputs: list[str]) -> None:
        """Store deterministic response text values.

        Args:
            outputs: Response text values in call order.
        """
        self._outputs = outputs
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        """Return the next configured response.

        Args:
            **kwargs: Captured Responses API arguments.

        Returns:
            An object exposing the expected ``output_text`` attribute.
        """
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self._outputs.pop(0))


class FakeClient:  # pylint: disable=too-few-public-methods
    """Provides the minimal OpenAI-compatible client required by the service."""

    def __init__(self, outputs: list[str]) -> None:
        """Create a client exposing a fake Responses resource.

        Args:
            outputs: Response text values in call order.
        """
        self.responses = FakeResponses(outputs)


def test_llm_nodes_extract_structured_request_and_generate_offer() -> None:
    """The graph nodes use separate OCI Responses calls for both responsibilities."""
    client = FakeClient(
        [
            '{"requested_object":"wireless ergonomic mouse","quantity":2}',
            "Offer: 2 × wireless ergonomic mouse at EUR 29 each. Total EUR 58. Assumed available.",
        ]
    )
    service = ProcurementLlmService(client_factory=lambda: client, model_id="model")

    intake = IntakeNode(service)({"message": "Order 2 wireless mice"})
    proposal = OfferNode(service)(intake)

    assert intake == {
        "requested_object": "wireless ergonomic mouse",
        "quantity": 2,
        "status": "generating_offer",
    }
    assert proposal["status"] == "awaiting_approval"
    assert "Total EUR 58" in proposal["draft"]
    assert client.responses.calls[0]["text"]["format"]["strict"] is True
    assert client.responses.calls[1]["input"] == (
        '{"requested_object":"wireless ergonomic mouse","quantity":2}'
    )


def test_llm_service_rejects_invalid_structured_output() -> None:
    """Invalid model JSON cannot enter durable workflow state."""
    service = ProcurementLlmService(
        client_factory=lambda: FakeClient(
            ['{"requested_object":"mouse","quantity":0}']
        ),
        model_id="model",
    )

    with pytest.raises(ProcurementInferenceError, match="invalid structured"):
        service.extract_request("Order a mouse")


def test_oci_endpoint_factory_normalizes_region() -> None:
    """The factory follows OCI's OpenAI-compatible regional endpoint pattern."""
    assert (
        build_oci_openai_base_url(" eu-frankfurt-1 ")
        == "https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com/openai/v1"
    )
    with pytest.raises(ValueError, match="REGION"):
        build_oci_openai_base_url(" ")


def test_status_reader_and_streamer_use_the_example04_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """State reconstruction and streaming use the local procurement graph."""
    application_module = importlib.import_module(
        "examples.example04_it_procurement.backend.app"
    )

    class FakeSnapshot:  # pylint: disable=too-few-public-methods
        """Provides a deterministic persisted state."""

        values = {
            "status": "awaiting_approval",
            "message": "Order 2 wireless mice",
            "draft": "Offer",
            "requested_object": "mouse",
            "quantity": 2,
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
    assert run_status.message == "Order 2 wireless mice"
    assert run_status.requested_object == "mouse"
    assert events[0].startswith("event: run_completed")


def test_run_summary_reader_lists_only_latest_example04_instances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The instance list ignores other examples and maps terminal runs correctly."""
    application_module = importlib.import_module(
        "examples.example04_it_procurement.backend.app"
    )
    checkpoint_tuples = [
        SimpleNamespace(
            config={"configurable": {"thread_id": "example04-completed"}},
            checkpoint={
                "ts": "2026-07-23T12:00:00+00:00",
                "channel_values": {"status": "ordered"},
            },
        ),
        SimpleNamespace(
            config={"configurable": {"thread_id": "example04-active"}},
            checkpoint={
                "ts": "2026-07-23T11:00:00+00:00",
                "channel_values": {"status": "awaiting_approval"},
            },
        ),
        SimpleNamespace(
            config={"configurable": {"thread_id": "example04-active"}},
            checkpoint={
                "ts": "2026-07-23T10:00:00+00:00",
                "channel_values": {"status": "ordered"},
            },
        ),
        SimpleNamespace(
            config={"configurable": {"thread_id": "example03-other"}},
            checkpoint={
                "ts": "2026-07-23T13:00:00+00:00",
                "channel_values": {"status": "ordered"},
            },
        ),
    ]

    class FakeSaver:  # pylint: disable=too-few-public-methods
        """Returns checkpoint tuples in newest-first order."""

        def __init__(self, _pool: Any) -> None:
            """Accept the pool passed by the application boundary."""

        def list(self, _config: None) -> Iterator[Any]:
            """Return fake durable checkpoints."""
            return iter(checkpoint_tuples)

    monkeypatch.setattr(application_module, "OracleSaver", FakeSaver)

    assert [summary.model_dump() for summary in read_run_summaries(object())] == [
        {
            "thread_id": "example04-completed",
            "status": "completed",
            "submitted_at": "2026-07-23T12:00:00+00:00",
        },
        {
            "thread_id": "example04-active",
            "status": "in_progress",
            "submitted_at": "2026-07-23T10:00:00+00:00",
        },
    ]


def test_api_resumes_once_and_acknowledges_repeated_decision() -> None:
    """A repeated final decision returns completion without graph execution."""
    streamer_calls: list[str] = []
    statuses = {
        "paused": RunStatus(
            thread_id="paused",
            status="awaiting_approval",
            message="Order 2 wireless mice",
            draft="Offer",
            requested_object="mouse",
            quantity=2,
            approval_required=True,
        ),
        "ordered": RunStatus(
            thread_id="ordered",
            status="ordered",
            message="Order 2 wireless mice",
            draft="Offer",
            requested_object="mouse",
            quantity=2,
            approval_decision="approve",
            approval_required=False,
        ),
    }

    def streamer(
        _pool: Any, thread_id: str, _graph_input: Any, _is_resume: bool
    ) -> Iterator[str]:
        """Record the invocation and produce a completion event.

        Yields:
            A deterministic completion SSE event.
        """
        streamer_calls.append(thread_id)
        yield format_sse("run_completed", {"thread_id": thread_id, "state": {}})

    application = importlib.import_module(
        "examples.example04_it_procurement.backend.app"
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
        "examples.example04_it_procurement.backend.app"
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


def test_api_lists_process_instances() -> None:
    """The list endpoint exposes only the UI-oriented instance fields."""
    application = importlib.import_module(
        "examples.example04_it_procurement.backend.app"
    ).create_app(
        initialize_database=False,
        run_list_reader=lambda _pool: [
            {
                "thread_id": "example04-active",
                "status": "in_progress",
                "submitted_at": "2026-07-23T12:00:00+00:00",
            },
            {
                "thread_id": "example04-completed",
                "status": "completed",
                "submitted_at": "2026-07-23T10:00:00+00:00",
            },
        ],
    )
    application.state.adb_pool = object()
    with TestClient(application) as client:
        response = client.get("/runs")

    assert response.status_code == 200
    assert response.json() == [
        {
            "thread_id": "example04-active",
            "status": "in_progress",
            "submitted_at": "2026-07-23T12:00:00+00:00",
        },
        {
            "thread_id": "example04-completed",
            "status": "completed",
            "submitted_at": "2026-07-23T10:00:00+00:00",
        },
    ]
