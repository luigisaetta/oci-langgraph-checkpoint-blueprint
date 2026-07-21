"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Defines the persisted state for the HITL LangGraph agent.
"""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """State shared by all Example 02 agent nodes.

    Attributes:
        message: Raw user request received by the API.
        normalized_message: Trimmed request prepared by the intake node.
        draft: Deterministic draft prepared for human review.
        status: Current lifecycle status of the agent run.
        approval_decision: Human decision returned after the HITL interrupt.
    """

    message: str
    normalized_message: str
    draft: str
    status: str
    approval_decision: str
