"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Pauses the HITL agent until a human approves or rejects its draft.
"""

from langgraph.types import interrupt

from examples.example02_hitl_sse.state import AgentState


class ApprovalNode:  # pylint: disable=too-few-public-methods
    """Requests a human decision for the draft and stores the result."""

    def __call__(self, state: AgentState) -> dict[str, str]:
        """Pause execution until the human approves or rejects the draft.

        Args:
            state: Current agent state containing the draft under review.

        Returns:
            State update containing the approval decision and final status.

        Raises:
            ValueError: If the resumed decision is not ``approve`` or ``reject``.
        """
        decision = interrupt(
            {
                "kind": "approval_request",
                "question": "Do you approve this draft?",
                "draft": state["draft"],
                "allowed_decisions": ["approve", "reject"],
            }
        )
        if decision not in {"approve", "reject"}:
            raise ValueError("The approval decision must be approve or reject.")
        return {
            "approval_decision": decision,
            "status": "approved" if decision == "approve" else "rejected",
        }
