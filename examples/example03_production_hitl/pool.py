"""
Author: L. Saetta
Date last modified: 2026-07-22
License: MIT
Description: Loads and creates the Oracle ADB connection pool used by Example 03.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import oracledb
from dotenv import dotenv_values

from utils.adb_connection import (
    ADBConnectionConfig,
    DEFAULT_ENV_FILE,
    load_connection_config,
)

POOL_VARIABLES = ("DB_POOL_MIN", "DB_POOL_MAX", "DB_POOL_INCREMENT")
NEXTJS_UI_ORIGIN_VARIABLE = "NEXTJS_UI_ORIGIN"
DEFAULT_NEXTJS_UI_ORIGIN = "http://127.0.0.1:3000"


class PoolConfigurationError(ValueError):
    """Raised when Example 03 connection-pool settings are invalid."""


class UIOriginConfigurationError(ValueError):
    """Raised when the configured Next.js development origin is invalid."""


@dataclass(frozen=True)
class PoolConfiguration:
    """Stores the validated Oracle connection-pool size settings.

    Attributes:
        minimum: Connections opened when the pool is created.
        maximum: Maximum connections that the pool may open.
        increment: Connections added when the pool needs to grow.
    """

    minimum: int
    maximum: int
    increment: int


def load_pool_configuration(
    environment: Mapping[str, str | None] | None = None,
    dotenv_path: Path = DEFAULT_ENV_FILE,
) -> PoolConfiguration:
    """Load and validate the Example 03 pool settings.

    Args:
        environment: Optional settings mapping for tests or programmatic use.
        dotenv_path: dotenv file read when ``environment`` is omitted.

    Returns:
        Validated pool configuration.

    Raises:
        PoolConfigurationError: If a required value is missing, non-numeric, or
            violates the pool size constraints.
    """
    if environment is None:
        environment = dotenv_values(dotenv_path=dotenv_path)

    values: dict[str, int] = {}
    for variable in POOL_VARIABLES:
        raw_value = (environment.get(variable) or "").strip()
        if not raw_value.isdigit() or int(raw_value) < 1:
            raise PoolConfigurationError(f"{variable} must be a positive integer.")
        values[variable] = int(raw_value)

    if values["DB_POOL_MIN"] > values["DB_POOL_MAX"]:
        raise PoolConfigurationError("DB_POOL_MIN must not exceed DB_POOL_MAX.")

    return PoolConfiguration(
        minimum=values["DB_POOL_MIN"],
        maximum=values["DB_POOL_MAX"],
        increment=values["DB_POOL_INCREMENT"],
    )


def create_adb_pool(
    connection_config: ADBConnectionConfig,
    pool_configuration: PoolConfiguration,
) -> Any:
    """Create a wallet-based Oracle connection pool for Example 03.

    Args:
        connection_config: Validated ADB connection settings.
        pool_configuration: Validated pool sizing settings.

    Returns:
        An open ``oracledb.ConnectionPool`` configured to wait for availability.
    """
    return oracledb.create_pool(
        **connection_config.as_connect_kwargs(),
        min=pool_configuration.minimum,
        max=pool_configuration.maximum,
        increment=pool_configuration.increment,
        getmode=oracledb.POOL_GETMODE_WAIT,
    )


def load_example03_configuration() -> tuple[ADBConnectionConfig, PoolConfiguration]:
    """Load the ADB and pool configuration from the shared local dotenv file.

    Returns:
        A pair containing the ADB connection configuration and pool settings.
    """
    environment = dotenv_values(dotenv_path=DEFAULT_ENV_FILE)
    return load_connection_config(environment), load_pool_configuration(environment)


def load_nextjs_ui_origin(
    environment: Mapping[str, str | None] | None = None,
    dotenv_path: Path = DEFAULT_ENV_FILE,
) -> str:
    """Load the allowed local Next.js UI origin for Example 04.

    Args:
        environment: Optional settings mapping for tests or programmatic use.
        dotenv_path: Dotenv file read when ``environment`` is omitted.

    Returns:
        A normalized HTTP(S) origin without a trailing slash.

    Raises:
        UIOriginConfigurationError: If the configured value is not a bare HTTP(S)
            origin.
    """
    if environment is None:
        environment = dotenv_values(dotenv_path=dotenv_path)

    origin = environment.get(NEXTJS_UI_ORIGIN_VARIABLE) or DEFAULT_NEXTJS_UI_ORIGIN
    normalized_origin = origin.strip().rstrip("/")
    parsed_origin = urlparse(normalized_origin)
    is_bare_origin = not any(
        (
            parsed_origin.path,
            parsed_origin.params,
            parsed_origin.query,
            parsed_origin.fragment,
        )
    )
    if (
        parsed_origin.scheme not in {"http", "https"}
        or not parsed_origin.netloc
        or not is_bare_origin
    ):
        raise UIOriginConfigurationError(
            f"{NEXTJS_UI_ORIGIN_VARIABLE} must be an HTTP(S) origin without a path."
        )
    return normalized_origin
