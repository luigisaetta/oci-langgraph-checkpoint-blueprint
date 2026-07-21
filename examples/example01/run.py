"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Runs a one-node LangGraph flow with Oracle ADB checkpoint persistence.
"""

from typing import TypedDict

import oracledb
from langgraph.graph import END, START, StateGraph
from langgraph_oracledb.checkpoint.oracle import OracleSaver

from utils.adb_connection import (
    ConnectionConfigurationError,
    create_adb_connection,
    load_connection_config,
)

EXAMPLE_THREAD_ID = "example01-thread"
EXAMPLE_MESSAGE = "hello ADB"


class ExampleState(TypedDict):
    """Defines the state persisted by the Example 01 graph.

    Attributes:
        message: Input message supplied when the graph starts.
        processed_message: Uppercase result produced by the only graph node.
    """

    message: str
    processed_message: str


def uppercase_message(state: ExampleState) -> dict[str, str]:
    """Convert the input message to uppercase.

    Args:
        state: Current graph state containing the input message.

    Returns:
        State update containing the uppercase message.
    """
    return {"processed_message": state["message"].upper()}


def build_graph() -> StateGraph:
    """Build the simple one-node graph used by this example.

    Returns:
        An uncompiled LangGraph state graph.
    """
    workflow = StateGraph(ExampleState)
    workflow.add_node("uppercase_message", uppercase_message)
    workflow.add_edge(START, "uppercase_message")
    workflow.add_edge("uppercase_message", END)
    return workflow


def run_example(message: str = EXAMPLE_MESSAGE) -> ExampleState:
    """Set up ADB checkpoint storage and run the example graph once.

    Args:
        message: Input message processed by the graph.

    Returns:
        Final graph state containing the input and processed message.

    Raises:
        ConnectionConfigurationError: If the local `.env` configuration is incomplete.
        oracledb.Error: If ADB connection or checkpoint operations fail.
    """
    config = load_connection_config()
    with create_adb_connection(config) as connection:
        checkpointer = OracleSaver(connection)
        checkpointer.setup()
        graph = build_graph().compile(checkpointer=checkpointer)
        result = graph.invoke(
            {"message": message},
            config={"configurable": {"thread_id": EXAMPLE_THREAD_ID}},
        )
    return result


def main() -> int:
    """Run Example 01 and print the non-sensitive execution result.

    Returns:
        ``0`` when the example completes, ``1`` for an ADB error, or ``2`` for
        missing local configuration.
    """
    try:
        result = run_example()
    except ConnectionConfigurationError as error:
        print(f"Example01 configuration error: {error}")
        return 2
    except (oracledb.Error, OSError) as error:
        print(
            "Example01 ADB execution failed "
            f"({type(error).__name__}). Check the local ADB configuration and network access."
        )
        return 1

    print("Example01 flow completed.")
    print(f"  Thread ID: {EXAMPLE_THREAD_ID}")
    print(f"  Input: {result['message']}")
    print(f"  Processed output: {result['processed_message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
