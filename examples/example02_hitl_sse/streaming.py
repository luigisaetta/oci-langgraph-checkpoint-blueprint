"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Converts LangGraph execution updates into server-sent events.
"""

import json
from collections.abc import Iterator
from typing import Any


def format_sse(event_name: str, payload: dict[str, Any]) -> str:
    """Format a JSON payload as one server-sent event.

    Args:
        event_name: SSE event name.
        payload: JSON-serializable event payload.

    Returns:
        A complete SSE message terminated by a blank line.
    """
    serialized_payload = json.dumps(payload, default=str, sort_keys=True)
    return f"event: {event_name}\ndata: {serialized_payload}\n\n"


def stream_graph_updates(
    graph: Any,
    graph_input: Any,
    thread_id: str,
    is_resume: bool = False,
) -> Iterator[str]:
    """Stream node updates and HITL interrupts from a compiled graph.

    Args:
        graph: Compiled LangGraph agent.
        graph_input: Initial state or a LangGraph resume command.
        thread_id: Persistent LangGraph thread identifier.
        is_resume: Whether this invocation resumes a paused run.

    Yields:
        Server-sent event strings describing agent progress and outcome.
    """
    config = {"configurable": {"thread_id": thread_id}}
    if not is_resume:
        yield format_sse("run_started", {"thread_id": thread_id})

    interrupted = False
    for chunk in graph.stream(
        graph_input,
        config=config,
        stream_mode="updates",
        version="v2",
    ):
        update = chunk["data"]
        interrupts = update.get("__interrupt__", ())
        if interrupts:
            interrupted = True
            for hitl_interrupt in interrupts:
                yield format_sse(
                    "approval_required",
                    {
                        "thread_id": thread_id,
                        "request": getattr(hitl_interrupt, "value", hitl_interrupt),
                    },
                )
            continue

        for node_name, state_update in update.items():
            yield format_sse(
                "node_update",
                {
                    "thread_id": thread_id,
                    "node": node_name,
                    "update": state_update,
                },
            )

    if not interrupted:
        final_state = graph.get_state(config).values
        yield format_sse(
            "run_completed",
            {"thread_id": thread_id, "state": final_state},
        )
