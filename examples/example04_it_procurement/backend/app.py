"""
Author: L. Saetta
Date last modified: 2026-07-23
License: MIT
Description: Exposes the durable Example 04 IT procurement agent through FastAPI.
"""

from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal
from uuid import uuid4

import oracledb
import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from langgraph_oracledb.checkpoint.oracle import OracleSaver
from pydantic import BaseModel, Field, field_validator

from examples.example02_hitl_sse.streaming import format_sse, stream_graph_updates
from examples.example03_production_hitl.pool import (
    create_adb_pool,
    load_example03_configuration,
    load_nextjs_ui_origin,
)
from examples.example04_it_procurement.backend.procurement_graph import (
    build_procurement_graph,
)

EXAMPLE_THREAD_ID_PREFIX = "example04-"
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
RunStreamer = Callable[[Any, str, Any, bool], Iterator[str]]


class StartRunRequest(BaseModel):
    """Defines the natural-language IT procurement request payload."""

    message: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        """Reject a request consisting only of whitespace.

        Args:
            value: Candidate procurement request.

        Returns:
            The accepted request.

        Raises:
            ValueError: If the request is blank after trimming.
        """
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class DecisionRequest(BaseModel):
    """Defines the human decision for a simulated purchase order."""

    decision: Literal["approve", "reject"]


class RunStatus(BaseModel):
    """Represents the persisted visible state of one procurement workflow."""

    thread_id: str
    status: str
    message: str | None = None
    draft: str | None = None
    requested_object: str | None = None
    quantity: int | None = None
    approval_decision: str | None = None
    approval_required: bool


def generate_thread_id() -> str:
    """Generate a durable thread identifier for an Example 04 procurement run.

    Returns:
        An ID prefixed with ``example04-``.
    """
    return f"{EXAMPLE_THREAD_ID_PREFIX}{uuid4().hex}"


def read_run_status(pool: Any, thread_id: str) -> RunStatus | None:
    """Load a persisted procurement workflow state from Oracle ADB.

    Args:
        pool: Oracle connection pool owned by the application.
        thread_id: Durable LangGraph thread identifier.

    Returns:
        The current state, or ``None`` when no checkpoint exists.
    """
    graph = build_procurement_graph(OracleSaver(pool))
    state_values = graph.get_state({"configurable": {"thread_id": thread_id}}).values
    if not state_values or "status" not in state_values:
        return None
    current_status = str(state_values["status"])
    return RunStatus(
        thread_id=thread_id,
        status=current_status,
        message=state_values.get("message"),
        draft=state_values.get("draft"),
        requested_object=state_values.get("requested_object"),
        quantity=state_values.get("quantity"),
        approval_decision=state_values.get("approval_decision"),
        approval_required=current_status == "awaiting_approval",
    )


def stream_run(
    pool: Any, thread_id: str, graph_input: Any, is_resume: bool
) -> Iterator[str]:
    """Stream a fresh or resumed procurement graph execution.

    Args:
        pool: Oracle connection pool owned by the application.
        thread_id: Durable workflow thread identifier.
        graph_input: Initial state or a LangGraph resume command.
        is_resume: Whether execution resumes a paused graph.

    Yields:
        SSE messages describing workflow progress or a safe failure.
    """
    try:
        graph = build_procurement_graph(OracleSaver(pool))
        yield from stream_graph_updates(graph, graph_input, thread_id, is_resume)
    except (oracledb.Error, OSError, RuntimeError, ValueError) as error:
        yield format_sse(
            "error",
            {
                "kind": "execution",
                "message": (
                    f"Procurement execution failed ({type(error).__name__}). "
                    "Check the request and ADB configuration."
                ),
            },
        )


def create_app(
    streamer: RunStreamer = stream_run,
    status_reader: Callable[[Any, str], RunStatus | None] = read_run_status,
    initialize_database: bool = True,
    ui_origin: str | None = None,
) -> FastAPI:
    """Create the Example 04 pooled, durable procurement API.

    Args:
        streamer: Graph execution function, injectable for tests.
        status_reader: Persisted-state reader, injectable for tests.
        initialize_database: Whether to create the ADB pool and schema.
        ui_origin: Explicit permitted Next.js browser origin.

    Returns:
        A FastAPI application.
    """

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> Iterator[None]:
        """Create and close the application-owned Oracle pool.

        Args:
            application: FastAPI application owning the pool.

        Yields:
            Control while the application is serving requests.
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
        title="Example 04 Durable IT Procurement Agent", lifespan=lifespan
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[ui_origin or load_nextjs_ui_origin()],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    application.state.adb_pool = None

    def get_pool(request: Request) -> Any:
        """Return the initialized pool or a safe service-unavailable response."""
        if request.app.state.adb_pool is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ADB connection pool is not ready.",
            )
        return request.app.state.adb_pool

    @application.get("/health/ready")
    def readiness(request: Request) -> dict[str, str]:
        """Confirm the pool can acquire a connection and validate it."""
        try:
            with get_pool(request).acquire() as connection:
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
        """Start and stream one durable procurement workflow."""
        return StreamingResponse(
            streamer(
                get_pool(request),
                generate_thread_id(),
                {"message": payload.message},
                False,
            ),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @application.get("/runs/{thread_id}", response_model=RunStatus)
    def get_run(thread_id: str, request: Request) -> RunStatus:
        """Return one persisted procurement workflow state."""
        run_status = status_reader(get_pool(request), thread_id)
        if run_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Run not found."
            )
        return run_status

    @application.post("/runs/{thread_id}/decision")
    def submit_decision(
        thread_id: str, payload: DecisionRequest, request: Request
    ) -> StreamingResponse:
        """Resume a paused order or acknowledge an idempotent final decision."""
        pool = get_pool(request)
        run_status = status_reader(pool, thread_id)
        if run_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Run not found."
            )
        if run_status.status in {"ordered", "rejected"}:
            if run_status.approval_decision == payload.decision:
                return StreamingResponse(
                    iter(
                        [
                            format_sse(
                                "run_completed",
                                {
                                    "thread_id": thread_id,
                                    "state": run_status.model_dump(),
                                    "idempotent": True,
                                },
                            )
                        ]
                    ),
                    media_type="text/event-stream",
                    headers=SSE_HEADERS,
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order is already complete with a different decision.",
            )
        if not run_status.approval_required:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order is not waiting for approval.",
            )
        return StreamingResponse(
            streamer(pool, thread_id, Command(resume=payload.decision), True),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    return application


app = create_app()


def main() -> None:
    """Run the Example 04 API on its dedicated local port."""
    uvicorn.run(
        "examples.example04_it_procurement.backend.app:app",
        host="127.0.0.1",
        port=8082,
        reload=True,
    )


if __name__ == "__main__":
    main()
