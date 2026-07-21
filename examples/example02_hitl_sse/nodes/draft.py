"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Produces a deterministic draft for human review.
"""

from examples.example02_hitl_sse.state import AgentState


class DraftNode:  # pylint: disable=too-few-public-methods
    """Creates a draft that the final node submits for human approval."""

    def call(self, state: AgentState) -> dict[str, str]:
        """Create a deterministic draft from the normalized user message.

        Args:
            state: Current agent state containing the normalized message.

        Returns:
            State update containing the draft and awaiting-approval status.
        """
        draft = f"Proposed response: {state['normalized_message']}"
        return {"draft": draft, "status": "awaiting_approval"}
