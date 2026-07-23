"""
Author: L. Saetta
Date last modified: 2026-07-23
License: MIT
Description: Builds the checkpointed LLM-assisted IT procurement LangGraph workflow.
"""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from examples.example04_it_procurement.backend.procurement_llm import (
    ProcurementLlmService,
    ProcurementRequest,
)


class ProcurementState(TypedDict, total=False):
    """Stores durable state for an LLM-assisted simulated procurement request."""

    message: str
    requested_object: str
    quantity: int
    draft: str
    status: str
    approval_decision: str


class IntakeNode:  # pylint: disable=too-few-public-methods
    """Uses an LLM to extract structured procurement data from the user request."""

    def __init__(self, llm_service: ProcurementLlmService) -> None:
        """Store the LLM service used during graph execution.

        Args:
            llm_service: OCI Responses API service.
        """
        self._llm_service = llm_service

    def __call__(self, state: ProcurementState) -> dict[str, str | int]:
        """Extract the requested object and quantity from the raw message.

        Args:
            state: Current graph state containing the user message.

        Returns:
            Structured request fields and the next lifecycle status.

        Raises:
            ValueError: If the raw message is blank.
        """
        message = state["message"].strip()
        if not message:
            raise ValueError("The procurement request must not be blank.")
        request = self._llm_service.extract_request(message)
        return {
            "requested_object": request.requested_object,
            "quantity": request.quantity,
            "status": "generating_offer",
        }


class OfferNode:  # pylint: disable=too-few-public-methods
    """Uses an LLM to generate an approval-ready simulated procurement offer."""

    def __init__(self, llm_service: ProcurementLlmService) -> None:
        """Store the LLM service used during graph execution.

        Args:
            llm_service: OCI Responses API service.
        """
        self._llm_service = llm_service

    def __call__(self, state: ProcurementState) -> dict[str, str]:
        """Generate an offer from the already extracted structured request.

        Args:
            state: Current graph state containing extracted request fields.

        Returns:
            A simulated offer and the approval-required lifecycle status.
        """
        request = ProcurementRequest(
            requested_object=state["requested_object"], quantity=state["quantity"]
        )
        return {
            "draft": self._llm_service.generate_offer(request),
            "status": "awaiting_approval",
        }


def approve_order(state: ProcurementState) -> dict[str, str]:
    """Pause for a human decision and record the simulated order outcome.

    Args:
        state: Current state containing the generated offer.

    Returns:
        The approval decision and final procurement lifecycle status.

    Raises:
        ValueError: If the resumed decision is not supported.
    """
    decision = interrupt(
        {
            "kind": "approval_request",
            "question": "Approve this simulated IT purchase order?",
            "draft": state["draft"],
            "requested_object": state["requested_object"],
            "quantity": state["quantity"],
            "allowed_decisions": ["approve", "reject"],
        }
    )
    if decision not in {"approve", "reject"}:
        raise ValueError("The approval decision must be approve or reject.")
    return {
        "approval_decision": decision,
        "status": "ordered" if decision == "approve" else "rejected",
    }


def build_procurement_graph(
    checkpointer: Any, llm_service: ProcurementLlmService | None = None
) -> Any:
    """Build the checkpointed LLM-assisted procurement workflow.

    Args:
        checkpointer: LangGraph-compatible checkpoint saver.
        llm_service: Optional injectable OCI service for tests.

    Returns:
        A compiled procurement graph.
    """
    service = llm_service or ProcurementLlmService()
    graph = StateGraph(ProcurementState)
    graph.add_node("intake", IntakeNode(service))
    graph.add_node("offer_generation", OfferNode(service))
    graph.add_node("order_approval", approve_order)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "offer_generation")
    graph.add_edge("offer_generation", "order_approval")
    graph.add_edge("order_approval", END)
    return graph.compile(checkpointer=checkpointer)
