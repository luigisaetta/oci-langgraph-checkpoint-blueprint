"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Builds the three-node human-in-the-loop LangGraph agent.
"""

from typing import Any

from langgraph.graph import END, START, StateGraph

from examples.example02_hitl_sse.nodes import ApprovalNode, DraftNode, IntakeNode
from examples.example02_hitl_sse.state import AgentState


def build_agent_graph(checkpointer: Any) -> Any:
    """Build and compile the Example 02 agent with the supplied checkpointer.

    Args:
        checkpointer: LangGraph-compatible saver, such as Oracle ``OracleSaver``.

    Returns:
        A compiled three-node LangGraph agent.
    """
    graph = StateGraph(AgentState)
    graph.add_node("intake", IntakeNode().call)
    graph.add_node("draft", DraftNode().call)
    graph.add_node("approval", ApprovalNode().call)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "draft")
    graph.add_edge("draft", "approval")
    graph.add_edge("approval", END)
    return graph.compile(checkpointer=checkpointer)
