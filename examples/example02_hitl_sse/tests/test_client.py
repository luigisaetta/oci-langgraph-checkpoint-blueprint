"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Tests the safe presentation header of the Example 02 Python client.
"""

from examples.example02_hitl_sse.client import format_client_header
from utils.adb_connection import ADBConnectionConfig


def test_client_header_displays_only_safe_connection_details() -> None:
    """The client header identifies the target without exposing passwords."""
    config = ADBConnectionConfig(
        user="demo_user",
        password="database-password",
        wallet_directory="/safe/local/wallet",
        wallet_password="wallet-password",
        dsn="demo_low",
    )

    header = format_client_header("http://127.0.0.1:8000", config)

    assert "Human-in-the-Loop Agent with FastAPI SSE" in header
    assert "API URL: http://127.0.0.1:8000" in header
    assert "DB_USER: demo_user" in header
    assert "DB_DSN: demo_low" in header
    assert "WALLET_DIR: /safe/local/wallet" in header
    assert "database-password" not in header
    assert "wallet-password" not in header
