"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Exposes the Example 02 HITL LangGraph agent through FastAPI SSE endpoints.
"""

from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal
from uuid import uuid4

import oracledb
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from langgraph_oracledb.checkpoint.oracle import OracleSaver
from pydantic import BaseModel, Field, field_validator

from examples.example02_hitl_sse.graph import build_agent_graph
from examples.example02_hitl_sse.streaming import format_sse, stream_graph_updates
from utils.adb_connection import (
    ConnectionConfigurationError,
    create_adb_connection,
    load_connection_config,
)

EXAMPLE_THREAD_ID_PREFIX = "example02-"
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
RunStreamer = Callable[[str, Any, bool], Iterator[str]]


class StartRunRequest(BaseModel):
    """Defines the payload used to start a new Example 02 agent run."""

    message: Annotated[str, Field(min_length=1, max_length=2_000)]

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        """Reject messages containing only whitespace.

        Args:
            value: Candidate user message.

        Returns:
            The accepted user message.

        Raises:
            ValueError: If the message is blank after whitespace trimming.
        """
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class DecisionRequest(BaseModel):
    """Defines the human decision used to resume an interrupted run."""

    decision: Literal["approve", "reject"]


def generate_thread_id() -> str:
    """Generate a unique persistent thread ID for one Example 02 run.

    Returns:
        A thread ID prefixed with ``example02-``.
    """
    return f"{EXAMPLE_THREAD_ID_PREFIX}{uuid4().hex}"


def initialize_checkpoint_schema() -> None:
    """Create or upgrade the ADB checkpoint schema during API startup.

    Raises:
        ConnectionConfigurationError: If local ADB settings are incomplete.
        oracledb.Error: If the ADB connection or migration cannot complete.
    """
    config = load_connection_config()
    with create_adb_connection(config) as connection:
        OracleSaver(connection).setup()


def stream_run(thread_id: str, graph_input: Any, is_resume: bool) -> Iterator[str]:
    """Open an ADB-backed graph and stream a run or resume operation.

    Args:
        thread_id: Persistent LangGraph thread identifier.
        graph_input: Initial graph state or ``Command(resume=...)``.
        is_resume: Whether this is a resume invocation.

    Yields:
        SSE messages produced by the agent run.
    """
    try:
        config = load_connection_config()
        with create_adb_connection(config) as connection:
            checkpointer = OracleSaver(connection)
            graph = build_agent_graph(checkpointer)
            yield from stream_graph_updates(
                graph,
                graph_input,
                thread_id,
                is_resume=is_resume,
            )
    except ConnectionConfigurationError as error:
        yield format_sse("error", {"kind": "configuration", "message": str(error)})
    except (oracledb.Error, OSError, ValueError) as error:
        yield format_sse(
            "error",
            {
                "kind": "execution",
                "message": (
                    f"Agent execution failed ({type(error).__name__}). "
                    "Check the ADB configuration, network access, and decision value."
                ),
            },
        )


def create_app(
    streamer: RunStreamer = stream_run,
    initialize_database: bool = True,
) -> FastAPI:
    """Create the Example 02 FastAPI application.

    Args:
        streamer: Function that executes the graph and yields SSE messages.
        initialize_database: Whether API startup initializes ADB checkpoint tables.

    Returns:
        Configured FastAPI application.
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> Iterator[None]:
        """Initialize checkpoint storage before accepting requests.

        Yields:
            Control to FastAPI after optional schema initialization.
        """
        if initialize_database:
            initialize_checkpoint_schema()
        yield

    application = FastAPI(
        title="Example 02 HITL SSE Agent",
        lifespan=lifespan,
    )

    @application.post("/runs")
    def start_run(payload: StartRunRequest) -> StreamingResponse:
        """Start a new agent thread and stream its progress.

        Args:
            payload: Request containing the agent message.

        Returns:
            SSE response containing node updates and an approval request.
        """
        thread_id = generate_thread_id()
        return StreamingResponse(
            streamer(thread_id, {"message": payload.message}, False),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @application.post("/runs/{thread_id}/decision")
    def submit_decision(
        thread_id: str,
        payload: DecisionRequest,
    ) -> StreamingResponse:
        """Resume an interrupted thread with a human approval decision.

        Args:
            thread_id: Thread ID emitted by the initial run stream.
            payload: Validated human decision.

        Returns:
            SSE response containing the resumed node update and final state.
        """
        return StreamingResponse(
            streamer(thread_id, Command(resume=payload.decision), True),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    return application


app = create_app()


def main() -> None:
    """Run the Example 02 FastAPI server with Uvicorn."""
    uvicorn.run(
        "examples.example02_hitl_sse.app:app",
        host="127.0.0.1",
        port=8080,
        reload=True,
    )


if __name__ == "__main__":
    main()
