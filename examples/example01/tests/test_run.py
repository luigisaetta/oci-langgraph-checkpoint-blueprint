"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Unit tests for the basic Oracle ADB checkpoint example.
"""

from examples.example01.run import build_graph
from utils.adb_connection import ADBConnectionConfig, create_adb_connection


def test_graph_uppercases_the_input_message() -> None:
    """The example graph produces the expected state update without ADB."""
    graph = build_graph().compile()

    result = graph.invoke({"message": "hello ADB"})

    assert result["processed_message"] == "HELLO ADB"


def test_create_adb_connection_passes_wallet_configuration() -> None:
    """The ADB connection factory passes wallet settings to the driver."""
    config = ADBConnectionConfig(
        user="example_user",
        password="database-password",
        wallet_directory="/local/wallet",
        wallet_password="wallet-password",
        dsn="example_low",
    )
    received_kwargs: dict[str, str] = {}
    expected_connection = object()

    def connector(**kwargs: str) -> object:
        received_kwargs.update(kwargs)
        return expected_connection

    connection = create_adb_connection(config, connector=connector)

    assert connection is expected_connection
    assert received_kwargs["user"] == "example_user"
    assert received_kwargs["dsn"] == "example_low"
    assert received_kwargs["config_dir"] == "/local/wallet"
    assert received_kwargs["wallet_location"] == "/local/wallet"
