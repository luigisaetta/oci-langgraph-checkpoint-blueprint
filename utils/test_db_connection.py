"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Safely validates a local Oracle Autonomous Database connection.
"""

from collections.abc import Callable, Mapping
from typing import Any

import oracledb
from utils.adb_connection import (
    ConnectionConfigurationError,
    create_adb_connection,
    format_connection_header,
    load_connection_config,
)


def check_connection(
    environment: Mapping[str, str | None] | None = None,
    connector: Callable[..., Any] = oracledb.connect,
    emit: Callable[[str], None] = print,
) -> int:
    """Connect to ADB, validate the session, and report a safe status message.

    Args:
        environment: Optional settings mapping. If omitted, configuration is loaded
            from the repository-root ``.env`` file.
        connector: Callable compatible with ``oracledb.connect``.
        emit: Function used to write messages for the command-line caller.

    Returns:
        ``0`` on success, ``1`` for a connection or validation failure, or ``2``
        when required configuration is missing.
    """
    try:
        config = load_connection_config(environment=environment)
    except ConnectionConfigurationError as error:
        emit(f"ADB connection configuration error: {error}")
        return 2

    emit(format_connection_header(config))
    connection = None
    try:
        connection = create_adb_connection(config, connector=connector)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM dual")
            cursor.fetchone()
    except (oracledb.Error, OSError) as error:
        emit(
            "ADB connection check failed "
            f"({type(error).__name__}). Check DB_USER, DB_PWD, WALLET_DIR, "
            "WALLET_PWD, and DB_DSN."
        )
        return 1
    finally:
        if connection is not None:
            connection.close()

    emit("ADB connection OK.")
    return 0


def main() -> int:
    """Run the ADB connectivity check as a command-line utility.

    Returns:
        Process exit status from :func:`check_connection`.
    """
    return check_connection()


if __name__ == "__main__":
    raise SystemExit(main())
