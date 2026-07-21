"""
Author: L. Saetta
Date last modified: 2026-07-21
License: MIT
Description: Loads safe local ADB configuration and creates wallet-based connections.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import oracledb
from dotenv import dotenv_values

REQUIRED_ENVIRONMENT_VARIABLES = (
    "DB_USER",
    "DB_PWD",
    "WALLET_DIR",
    "WALLET_PWD",
    "DB_DSN",
)
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = REPOSITORY_ROOT / ".env"


class ConnectionConfigurationError(ValueError):
    """Raised when required ADB connection settings are unavailable."""


@dataclass(frozen=True)
class ADBConnectionConfig:
    """Holds the configuration required for an ADB Thin-mode connection.

    Attributes:
        user: Oracle database user name.
        password: Password for the Oracle database user.
        wallet_directory: Directory containing the extracted ADB wallet files.
        wallet_password: Password assigned when downloading the wallet.
        dsn: ADB service alias or Oracle connection string.
    """

    user: str
    password: str
    wallet_directory: str
    wallet_password: str
    dsn: str

    def as_connect_kwargs(self) -> dict[str, str]:
        """Build keyword arguments for ``oracledb.connect``.

        Returns:
            Oracle connection arguments for a wallet-based ADB connection.
        """
        return {
            "user": self.user,
            "password": self.password,
            "dsn": self.dsn,
            "config_dir": self.wallet_directory,
            "wallet_location": self.wallet_directory,
            "wallet_password": self.wallet_password,
        }


def load_connection_config(
    environment: Mapping[str, str | None] | None = None,
    dotenv_path: Path = DEFAULT_ENV_FILE,
) -> ADBConnectionConfig:
    """Load and validate ADB connection settings without exposing their values.

    Args:
        environment: Optional settings mapping for programmatic use or tests. When
            omitted, settings are read from the repository-root ``.env`` file.
        dotenv_path: Path to the dotenv file used when ``environment`` is omitted.

    Returns:
        Validated ADB connection configuration.

    Raises:
        ConnectionConfigurationError: If one or more required variables are absent
            or blank.
    """
    if environment is None:
        environment = dotenv_values(dotenv_path=dotenv_path)

    missing_variables = [
        variable
        for variable in REQUIRED_ENVIRONMENT_VARIABLES
        if not (environment.get(variable) or "").strip()
    ]
    if missing_variables:
        missing_names = ", ".join(missing_variables)
        raise ConnectionConfigurationError(
            f"Missing required environment variables: {missing_names}."
        )

    return ADBConnectionConfig(
        user=environment["DB_USER"] or "",
        password=environment["DB_PWD"] or "",
        wallet_directory=environment["WALLET_DIR"] or "",
        wallet_password=environment["WALLET_PWD"] or "",
        dsn=environment["DB_DSN"] or "",
    )


def format_connection_header(config: ADBConnectionConfig) -> str:
    """Create a safe, human-readable summary of the connection attempt.

    Args:
        config: Validated ADB connection configuration.

    Returns:
        A header containing only non-sensitive connection parameters.
    """
    return "\n".join(
        (
            "Oracle ADB connection parameters:",
            f"  DB_USER: {config.user}",
            f"  DB_DSN: {config.dsn}",
            f"  WALLET_DIR: {config.wallet_directory}",
        )
    )


def create_adb_connection(
    config: ADBConnectionConfig,
    connector: Callable[..., Any] = oracledb.connect,
) -> Any:
    """Create a wallet-based Oracle ADB connection.

    Args:
        config: Validated local ADB connection configuration.
        connector: Callable compatible with ``oracledb.connect``.

    Returns:
        An open Oracle database connection.
    """
    return connector(**config.as_connect_kwargs())
