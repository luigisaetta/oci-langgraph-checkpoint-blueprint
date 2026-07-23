"""
Author: L. Saetta
Date last modified: 2026-07-23
License: MIT
Description: Builds the deterministic IT procurement LangGraph workflow.
"""

import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


class ProcurementState(TypedDict, total=False):
    """Stores the durable state of one simulated IT procurement request."""

    message: str
    normalized_message: str
    quantity: int
    products: list[dict[str, str | int]]
    draft: str
    status: str
    approval_decision: str


CATALOGUE = (
    {
        "sku": "MOU-100",
        "name": "Wireless Ergonomic Mouse",
        "keywords": "mouse mice wireless ergonomic",
        "unit_price_eur": 29,
    },
    {
        "sku": "KEY-200",
        "name": "Compact Wireless Keyboard",
        "keywords": "keyboard keyboards tastiera tastiere wireless",
        "unit_price_eur": 49,
    },
    {
        "sku": "PHO-300",
        "name": "Business Android Phone",
        "keywords": "phone phones mobile cellular smartphone cellulare cellulari telefono telefoni",
        "unit_price_eur": 399,
    },
    {
        "sku": "BAT-400",
        "name": "USB-C Rechargeable Battery Pack",
        "keywords": "battery batteries batteria batterie power bank usb-c",
        "unit_price_eur": 39,
    },
)


def requested_quantity(message: str) -> int:
    """Return the requested positive quantity, defaulting to one unit.

    Args:
        message: Normalized procurement request.

    Returns:
        A positive requested quantity capped at 99 for this demonstration.
    """
    match = re.search(r"\b(\d{1,2})\b", message)
    return int(match.group(1)) if match and int(match.group(1)) > 0 else 1


def matching_products(message: str) -> list[dict[str, str | int]]:
    """Find deterministic catalogue products matching the request words.

    Args:
        message: Normalized user request.

    Returns:
        Catalogue products whose keywords occur in the request.
    """
    request_words = set(re.findall(r"[a-z0-9-]+", message.lower()))
    return [
        {key: value for key, value in product.items() if key != "keywords"}
        for product in CATALOGUE
        if request_words.intersection(product["keywords"].split())
    ]


def intake_request(state: ProcurementState) -> dict[str, str | int]:
    """Normalize a procurement request and derive its requested quantity.

    Args:
        state: Current durable workflow state.

    Returns:
        The normalized request, quantity, and next lifecycle status.

    Raises:
        ValueError: If the request is blank after normalization.
    """
    normalized_message = state["message"].strip()
    if not normalized_message:
        raise ValueError("The procurement request must not be blank.")
    return {
        "normalized_message": normalized_message,
        "quantity": requested_quantity(normalized_message),
        "status": "searching_catalogue",
    }


def create_order_proposal(state: ProcurementState) -> dict[str, Any]:
    """Search the catalogue and create a deterministic simulated order proposal.

    Args:
        state: Current state after request intake.

    Returns:
        Matching products, a user-reviewable proposal, and an approval status.
    """
    products = matching_products(state["normalized_message"])
    quantity = state["quantity"]
    if not products:
        draft = (
            "No catalogue products matched this request. Update the request with "
            "a supported IT product, such as mouse, keyboard, phone, or battery."
        )
    else:
        lines = [
            f"{quantity} × {product['name']} ({product['sku']}) — "
            f"EUR {int(product['unit_price_eur']) * quantity}"
            for product in products
        ]
        total = sum(int(product["unit_price_eur"]) * quantity for product in products)
        draft = (
            "Simulated purchase order:\n" + "\n".join(lines) + f"\nTotal: EUR {total}"
        )
    return {"products": products, "draft": draft, "status": "awaiting_approval"}


def approve_order(state: ProcurementState) -> dict[str, str]:
    """Pause for a human decision and record the simulated order outcome.

    Args:
        state: Current state containing the proposed order.

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
            "products": state["products"],
            "allowed_decisions": ["approve", "reject"],
        }
    )
    if decision not in {"approve", "reject"}:
        raise ValueError("The approval decision must be approve or reject.")
    return {
        "approval_decision": decision,
        "status": "ordered" if decision == "approve" else "rejected",
    }


def build_procurement_graph(checkpointer: Any) -> Any:
    """Build the checkpointed IT procurement workflow.

    Args:
        checkpointer: LangGraph-compatible checkpoint saver.

    Returns:
        A compiled deterministic procurement graph.
    """
    graph = StateGraph(ProcurementState)
    graph.add_node("intake", intake_request)
    graph.add_node("catalogue_search", create_order_proposal)
    graph.add_node("order_approval", approve_order)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "catalogue_search")
    graph.add_edge("catalogue_search", "order_approval")
    graph.add_edge("order_approval", END)
    return graph.compile(checkpointer=checkpointer)
