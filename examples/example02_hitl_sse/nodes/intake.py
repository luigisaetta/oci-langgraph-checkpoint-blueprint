"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Normalizes the user request at the start of the HITL agent flow.
"""

from examples.example02_hitl_sse.state import AgentState


class IntakeNode:  # pylint: disable=too-few-public-methods
    """Accepts and normalizes the raw message supplied to the agent."""

    def __call__(self, state: AgentState) -> dict[str, str]:
        """Normalize the incoming message and mark it ready for drafting.

        Args:
            state: Current agent state containing the raw message.

        Returns:
            State update containing the normalized message and lifecycle status.

        Raises:
            ValueError: If the message is blank after trimming whitespace.
        """
        normalized_message = state["message"].strip()
        if not normalized_message:
            raise ValueError("The agent message must not be blank.")
        return {"normalized_message": normalized_message, "status": "drafting"}
