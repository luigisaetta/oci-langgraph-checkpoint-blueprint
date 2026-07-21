"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Tests the Example 02 node updates and human-in-the-loop resume flow.
"""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from examples.example02_hitl_sse.graph import build_agent_graph
from examples.example02_hitl_sse.nodes import DraftNode, IntakeNode


def test_intake_and_draft_nodes_transform_the_agent_state() -> None:
    """The first two nodes normalize the message and produce a draft."""
    intake_update = IntakeNode()({"message": "  prepare report  "})
    draft_update = DraftNode()(
        {"normalized_message": intake_update["normalized_message"]}
    )

    assert intake_update == {
        "normalized_message": "prepare report",
        "status": "drafting",
    }
    assert draft_update == {
        "draft": "Proposed response: prepare report",
        "status": "awaiting_approval",
    }


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [("approve", "approved"), ("reject", "rejected")],
)
def test_graph_interrupts_and_resumes_with_human_decision(
    decision: str,
    expected_status: str,
) -> None:
    """The same in-memory thread resumes from the approval interrupt."""
    graph = build_agent_graph(InMemorySaver())
    config = {"configurable": {"thread_id": f"test-{decision}"}}

    chunks = list(
        graph.stream(
            {"message": "prepare quarterly report"},
            config=config,
            stream_mode="updates",
            version="v2",
        )
    )
    updates = [chunk["data"] for chunk in chunks if chunk["type"] == "updates"]

    assert updates[0]["intake"]["status"] == "drafting"
    assert updates[1]["draft"]["status"] == "awaiting_approval"
    assert "__interrupt__" in updates[2]

    list(
        graph.stream(
            Command(resume=decision),
            config=config,
            stream_mode="updates",
            version="v2",
        )
    )
    final_state = graph.get_state(config).values

    assert final_state["approval_decision"] == decision
    assert final_state["status"] == expected_status
