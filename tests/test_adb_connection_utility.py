"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Unit tests for the Oracle Autonomous Database connectivity utility.
"""

import oracledb

from utils.test_db_connection import check_connection

VALID_ENVIRONMENT = {
    "DB_USER": "demo_user",
    "DB_PWD": "database-password",
    "WALLET_DIR": "/safe/local/wallet",
    "WALLET_PWD": "wallet-password",
    "DB_DSN": "demo_low",
}


class FakeCursor:
    """Records the validation SQL issued by the connection utility."""

    def __init__(self) -> None:
        """Initialise the cursor with no executed statements."""
        self.executed_statement: str | None = None

    def __enter__(self) -> "FakeCursor":
        """Enter the cursor context.

        Returns:
            The fake cursor instance.
        """
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Exit the cursor context without suppressing any exception."""
        return None

    def execute(self, statement: str) -> None:
        """Record the supplied SQL statement.

        Args:
            statement: SQL submitted by the utility.
        """
        self.executed_statement = statement

    def fetchone(self) -> tuple[int]:
        """Return the expected result of the ADB validation query.

        Returns:
            A single row containing ``1``.
        """
        return (1,)


class FakeConnection:
    """Minimal database connection fake for unit tests."""

    def __init__(self) -> None:
        """Initialise the fake connection and its cursor."""
        self.cursor_instance = FakeCursor()
        self.closed = False

    def cursor(self) -> FakeCursor:
        """Return the cursor used to validate the database session.

        Returns:
            A fake cursor.
        """
        return self.cursor_instance

    def close(self) -> None:
        """Record that the database connection was closed."""
        self.closed = True


def test_check_connection_reports_success_and_closes_connection() -> None:
    """The utility validates a live connection and reports a success message."""
    connection = FakeConnection()
    received_kwargs: dict[str, str] = {}
    messages: list[str] = []

    def connector(**kwargs: str) -> FakeConnection:
        received_kwargs.update(kwargs)
        return connection

    exit_code = check_connection(
        environment=VALID_ENVIRONMENT,
        connector=connector,
        emit=messages.append,
    )

    assert exit_code == 0
    assert received_kwargs["config_dir"] == VALID_ENVIRONMENT["WALLET_DIR"]
    assert received_kwargs["wallet_location"] == VALID_ENVIRONMENT["WALLET_DIR"]
    assert connection.cursor_instance.executed_statement == "SELECT 1 FROM dual"
    assert connection.closed is True
    assert messages[0] == (
        "Oracle ADB connection parameters:\n"
        "  DB_USER: demo_user\n"
        "  DB_DSN: demo_low\n"
        "  WALLET_DIR: /safe/local/wallet"
    )
    assert messages[1] == "ADB connection OK."
    assert VALID_ENVIRONMENT["DB_PWD"] not in "\n".join(messages)
    assert VALID_ENVIRONMENT["WALLET_PWD"] not in "\n".join(messages)


def test_check_connection_reports_missing_configuration_without_values() -> None:
    """The utility names missing variables but does not expose any secret values."""
    messages: list[str] = []
    incomplete_environment = {"DB_USER": "demo_user", "DB_PWD": "secret-value"}

    exit_code = check_connection(
        environment=incomplete_environment,
        emit=messages.append,
    )

    assert exit_code == 2
    assert "WALLET_DIR, WALLET_PWD, DB_DSN" in messages[0]
    assert "secret-value" not in messages[0]


def test_check_connection_reports_connection_failure_without_secret_values() -> None:
    """The utility returns a safe, clear error if the database rejects a session."""
    messages: list[str] = []

    def failing_connector(**kwargs: str) -> FakeConnection:
        raise oracledb.DatabaseError("connection rejected")

    exit_code = check_connection(
        environment=VALID_ENVIRONMENT,
        connector=failing_connector,
        emit=messages.append,
    )

    assert exit_code == 1
    assert messages[0].startswith("Oracle ADB connection parameters:")
    assert "ADB connection check failed (DatabaseError)" in messages[1]
    assert VALID_ENVIRONMENT["DB_PWD"] not in "\n".join(messages)
    assert VALID_ENVIRONMENT["WALLET_PWD"] not in "\n".join(messages)
