"""
Author: L. Saetta
Date last modified: 2026-07-22
License: MIT
Description: Exposes an ADB-pooled, restart-recoverable HITL agent through FastAPI.
"""

from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal
from uuid import uuid4

import oracledb
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from langgraph_oracledb.checkpoint.oracle import OracleSaver
from pydantic import BaseModel, Field, field_validator

from examples.example02_hitl_sse.graph import build_agent_graph
from examples.example02_hitl_sse.streaming import format_sse, stream_graph_updates
from examples.example03_production_hitl.pool import (
    create_adb_pool,
    load_example03_configuration,
)

EXAMPLE_THREAD_ID_PREFIX = "example03-"
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
RunStreamer = Callable[[Any, str, Any, bool], Iterator[str]]
StatusReader = Callable[[Any, str], "RunStatus | None"]


class StartRunRequest(BaseModel):
    """Defines the input payload used to start an Example 03 run."""

    message: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        """Reject an input consisting only of whitespace.

        Args:
            value: Candidate user message.

        Returns:
            The accepted message.

        Raises:
            ValueError: If the input is blank after trimming.
        """
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class DecisionRequest(BaseModel):
    """Defines the approval decision used to resume a durable thread."""

    decision: Literal["approve", "reject"]


class RunStatus(BaseModel):
    """Represents the persisted, externally visible state of one workflow."""

    thread_id: str
    status: str
    draft: str | None = None
    approval_decision: str | None = None
    approval_required: bool


def generate_thread_id() -> str:
    """Generate a unique durable thread ID for one Example 03 run.

    Returns:
        An ID prefixed with ``example03-``.
    """
    return f"{EXAMPLE_THREAD_ID_PREFIX}{uuid4().hex}"


def read_run_status(pool: Any, thread_id: str) -> RunStatus | None:
    """Load a workflow's current state through the ADB-backed checkpointer.

    Args:
        pool: Oracle connection pool owned by the FastAPI application.
        thread_id: Durable LangGraph thread identifier.

    Returns:
        The current workflow status, or ``None`` when no checkpoint exists.
    """
    graph = build_agent_graph(OracleSaver(pool))
    snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
    state_values = snapshot.values
    if not state_values or "status" not in state_values:
        return None
    current_status = str(state_values["status"])
    return RunStatus(
        thread_id=thread_id,
        status=current_status,
        draft=state_values.get("draft"),
        approval_decision=state_values.get("approval_decision"),
        approval_required=current_status == "awaiting_approval",
    )


def stream_run(
    pool: Any, thread_id: str, graph_input: Any, is_resume: bool
) -> Iterator[str]:
    """Stream a fresh or resumed graph execution using the application pool.

    Args:
        pool: Oracle connection pool owned by the FastAPI application.
        thread_id: Persistent LangGraph thread identifier.
        graph_input: Initial state or a LangGraph resume command.
        is_resume: Whether this invocation resumes a paused graph.

    Yields:
        SSE messages describing workflow progress or a safe execution failure.
    """
    try:
        graph = build_agent_graph(OracleSaver(pool))
        yield from stream_graph_updates(graph, graph_input, thread_id, is_resume)
    except (oracledb.Error, OSError, ValueError) as error:
        yield format_sse(
            "error",
            {
                "kind": "execution",
                "message": (
                    f"Agent execution failed ({type(error).__name__}). "
                    "Check the ADB configuration, pool capacity, and decision value."
                ),
            },
        )


def _completed_event(run_status: RunStatus, idempotent: bool) -> Iterator[str]:
    """Return one completed SSE event for an already terminal workflow.

    Args:
        run_status: Persisted terminal status.
        idempotent: Whether this response acknowledges a repeated decision.

    Yields:
        A completed SSE event without invoking the graph.
    """
    yield format_sse(
        "run_completed",
        {
            "thread_id": run_status.thread_id,
            "state": run_status.model_dump(),
            "idempotent": idempotent,
        },
    )


def create_app(
    streamer: RunStreamer = stream_run,
    status_reader: StatusReader = read_run_status,
    initialize_database: bool = True,
) -> FastAPI:
    """Create the Example 03 FastAPI application.

    Args:
        streamer: Function that runs the graph and produces SSE events.
        status_reader: Function that reads persisted workflow state.
        initialize_database: Whether the lifespan creates the ADB pool and schema.

    Returns:
        A FastAPI application configured for pooled durable workflows.
    """

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> Iterator[None]:
        """Create the pool and checkpoint schema before serving requests.

        Args:
            application: FastAPI application that owns the pool.

        Yields:
            Control after optional pool and schema initialization.
        """
        pool = None
        if initialize_database:
            connection_config, pool_configuration = load_example03_configuration()
            pool = create_adb_pool(connection_config, pool_configuration)
            OracleSaver(pool).setup()
            application.state.adb_pool = pool
        try:
            yield
        finally:
            if pool is not None:
                pool.close()

    application = FastAPI(
        title="Example 03 Production HITL Recovery Agent",
        lifespan=lifespan,
    )
    application.state.adb_pool = None

    def get_pool(request: Request) -> Any:
        """Return the application-owned pool or report an unavailable service.

        Args:
            request: Current FastAPI request.

        Returns:
            The initialized Oracle connection pool.

        Raises:
            HTTPException: If the pool is not available.
        """
        pool = request.app.state.adb_pool
        if pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ADB connection pool is not ready.",
            )
        return pool

    @application.get("/health/ready")
    def readiness(request: Request) -> dict[str, str]:
        """Confirm that a pool connection can execute a validation query.

        Args:
            request: Current FastAPI request.

        Returns:
            Readiness status.

        Raises:
            HTTPException: If the pool cannot supply a usable connection.
        """
        pool = get_pool(request)
        try:
            with pool.acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM dual")
                    cursor.fetchone()
        except oracledb.Error as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ADB connection pool is not ready.",
            ) from error
        return {"status": "ready"}

    @application.post("/runs")
    def start_run(payload: StartRunRequest, request: Request) -> StreamingResponse:
        """Start a workflow and stream it until completion or interruption.

        Args:
            payload: Validated workflow message.
            request: Current FastAPI request.

        Returns:
            SSE response containing the workflow progress.
        """
        thread_id = generate_thread_id()
        return StreamingResponse(
            streamer(get_pool(request), thread_id, {"message": payload.message}, False),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @application.get("/runs/{thread_id}", response_model=RunStatus)
    def get_run(thread_id: str, request: Request) -> RunStatus:
        """Return the durable state of one workflow thread.

        Args:
            thread_id: Persistent LangGraph thread identifier.
            request: Current FastAPI request.

        Returns:
            Persisted workflow status.

        Raises:
            HTTPException: If no checkpoint exists for the thread.
        """
        run_status = status_reader(get_pool(request), thread_id)
        if run_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Run not found."
            )
        return run_status

    @application.post("/runs/{thread_id}/decision")
    def submit_decision(
        thread_id: str,
        payload: DecisionRequest,
        request: Request,
    ) -> StreamingResponse:
        """Resume a paused workflow or acknowledge a repeated final decision.

        Args:
            thread_id: Persistent LangGraph thread identifier.
            payload: Validated human decision.
            request: Current FastAPI request.

        Returns:
            SSE response containing completion or resumed workflow progress.

        Raises:
            HTTPException: If the run is unknown, terminal with a conflicting
                decision, or not waiting for approval.
        """
        pool = get_pool(request)
        run_status = status_reader(pool, thread_id)
        if run_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Run not found."
            )
        if run_status.status in {"approved", "rejected"}:
            if run_status.approval_decision == payload.decision:
                return StreamingResponse(
                    _completed_event(run_status, idempotent=True),
                    media_type="text/event-stream",
                    headers=SSE_HEADERS,
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Run is already complete with a different decision.",
            )
        if not run_status.approval_required:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Run is not waiting for approval.",
            )
        return StreamingResponse(
            streamer(pool, thread_id, Command(resume=payload.decision), True),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    return application


app = create_app()


def main() -> None:
    """Run the Example 03 FastAPI service using the default local port."""
    uvicorn.run(
        "examples.example03_production_hitl.app:app",
        host="127.0.0.1",
        port=8081,
        reload=True,
    )


if __name__ == "__main__":
    main()
