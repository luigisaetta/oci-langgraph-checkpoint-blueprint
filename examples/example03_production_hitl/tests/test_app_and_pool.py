"""
Author: L. Saetta
Date last modified: 2026-07-22
License: MIT
Description: Tests pool validation and durable recovery API behaviour without ADB.
"""

from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from examples.example02_hitl_sse.streaming import format_sse
from examples.example03_production_hitl import app as example_app
from examples.example03_production_hitl.app import (
    RunStatus,
    create_app,
    read_run_status,
    stream_run,
)
from examples.example03_production_hitl.pool import (
    create_adb_pool,
    PoolConfigurationError,
    UIOriginConfigurationError,
    load_nextjs_ui_origin,
    load_pool_configuration,
)


def test_pool_configuration_rejects_invalid_sizes() -> None:
    """Pool configuration requires positive values and a valid min/max range."""
    with pytest.raises(PoolConfigurationError, match="DB_POOL_MIN"):
        load_pool_configuration(
            {"DB_POOL_MIN": "3", "DB_POOL_MAX": "2", "DB_POOL_INCREMENT": "1"}
        )


def test_nextjs_ui_origin_requires_a_bare_http_origin() -> None:
    """The API permits one explicit browser origin and rejects URL paths."""
    assert (
        load_nextjs_ui_origin({"NEXTJS_UI_ORIGIN": "http://localhost:3000/"})
        == "http://localhost:3000"
    )
    with pytest.raises(UIOriginConfigurationError, match="NEXTJS_UI_ORIGIN"):
        load_nextjs_ui_origin({"NEXTJS_UI_ORIGIN": "https://ui.example/app"})

    with pytest.raises(PoolConfigurationError, match="DB_POOL_INCREMENT"):
        load_pool_configuration(
            {"DB_POOL_MIN": "1", "DB_POOL_MAX": "2", "DB_POOL_INCREMENT": "zero"}
        )


def test_pool_factory_forwards_validated_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pool factory forwards wallet settings and validated sizing values."""
    configuration = load_pool_configuration(
        {"DB_POOL_MIN": "2", "DB_POOL_MAX": "6", "DB_POOL_INCREMENT": "2"}
    )
    create_pool = Mock(return_value="pool")
    monkeypatch.setattr(
        "examples.example03_production_hitl.pool.oracledb.create_pool", create_pool
    )
    connection = Mock()
    connection.as_connect_kwargs.return_value = {"user": "schema", "dsn": "adb"}

    assert create_adb_pool(connection, configuration) == "pool"
    assert create_pool.call_args.kwargs["min"] == 2
    assert create_pool.call_args.kwargs["max"] == 6
    assert create_pool.call_args.kwargs["increment"] == 2


def test_status_reader_and_streamer_use_the_pool_without_adb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Status reconstruction and streaming share a pool-backed OracleSaver."""

    class FakeSnapshot:  # pylint: disable=too-few-public-methods
        """Provides a persisted workflow state."""

        values = {
            "status": "awaiting_approval",
            "draft": "Draft",
            "approval_decision": None,
        }

    class FakeGraph:  # pylint: disable=too-few-public-methods
        """Provides a snapshot for the graph state reader."""

        def get_state(self, _config: dict[str, Any]) -> FakeSnapshot:
            """Return the deterministic fake state."""
            return FakeSnapshot()

    monkeypatch.setattr(example_app, "build_agent_graph", lambda _saver: FakeGraph())
    monkeypatch.setattr(
        example_app,
        "stream_graph_updates",
        lambda *_args: iter([format_sse("run_completed", {"thread_id": "thread"})]),
    )

    run_status = read_run_status(object(), "thread")
    events = list(stream_run(object(), "thread", {"message": "hello"}, False))

    assert run_status.status == "awaiting_approval"
    assert run_status.approval_required is True
    assert events[0].startswith("event: run_completed")


def test_readiness_acquires_a_connection_and_main_uses_example_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Readiness validates a borrowed connection and the entry point uses 8081."""

    class FakeCursor:
        """Supplies a context-managed validation cursor."""

        def __enter__(self) -> "FakeCursor":
            """Enter the cursor context."""
            return self

        def __exit__(self, *_args: Any) -> None:
            """Exit the cursor context."""

        def execute(self, query: str) -> None:
            """Validate the expected query."""
            assert query == "SELECT 1 FROM dual"

        def fetchone(self) -> tuple[int]:
            """Return the validation-query result."""
            return (1,)

    class FakeConnection:
        """Supplies a validation cursor."""

        def __enter__(self) -> "FakeConnection":
            """Enter the connection context."""
            return self

        def __exit__(self, *_args: Any) -> None:
            """Exit the connection context."""

        def cursor(self) -> FakeCursor:
            """Return the fake cursor."""
            return FakeCursor()

    class FakePool:  # pylint: disable=too-few-public-methods
        """Supplies a borrowed connection."""

        def acquire(self) -> FakeConnection:
            """Borrow a fake connection."""
            return FakeConnection()

    application = create_app(initialize_database=False)
    application.state.adb_pool = FakePool()
    with TestClient(application) as client:
        assert client.get("/health/ready").json() == {"status": "ready"}

    run_server = Mock()
    monkeypatch.setattr(example_app.uvicorn, "run", run_server)
    example_app.main()
    assert run_server.call_args.kwargs["port"] == 8081


def test_api_allows_only_the_configured_nextjs_origin() -> None:
    """The Example 04 browser origin is explicitly permitted through CORS."""
    application = create_app(
        initialize_database=False, ui_origin="http://127.0.0.1:3000"
    )
    application.state.adb_pool = object()
    with TestClient(application) as client:
        response = client.options(
            "/runs",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        rejected_response = client.options(
            "/runs",
            headers={
                "Origin": "http://127.0.0.1:3001",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert rejected_response.status_code == 400


def test_status_and_sequential_decision_idempotency_without_database() -> None:
    """The API exposes state and does not re-run an already completed decision."""
    streamer_calls: list[str] = []
    statuses = {
        "paused": RunStatus(
            thread_id="paused",
            status="awaiting_approval",
            draft="Draft",
            approval_required=True,
        ),
        "approved": RunStatus(
            thread_id="approved",
            status="approved",
            approval_decision="approve",
            approval_required=False,
        ),
    }

    def streamer(
        _pool: Any, thread_id: str, _input: Any, _resume: bool
    ) -> Iterator[str]:
        streamer_calls.append(thread_id)
        yield format_sse("run_completed", {"thread_id": thread_id, "state": {}})

    def status_reader(_pool: Any, thread_id: str) -> RunStatus | None:
        return statuses.get(thread_id)

    application = create_app(
        streamer=streamer,
        status_reader=status_reader,
        initialize_database=False,
    )
    application.state.adb_pool = object()
    with TestClient(application) as client:
        paused = client.get("/runs/paused")
        missing = client.get("/runs/missing")
        resume = client.post("/runs/paused/decision", json={"decision": "approve"})
        repeated = client.post("/runs/approved/decision", json={"decision": "approve"})
        conflicting = client.post(
            "/runs/approved/decision", json={"decision": "reject"}
        )

    assert paused.status_code == 200
    assert paused.json()["approval_required"] is True
    assert missing.status_code == 404
    assert resume.status_code == 200
    assert streamer_calls == ["paused"]
    assert repeated.status_code == 200
    assert '"idempotent": true' in repeated.text
    assert conflicting.status_code == 409
