# Specification: Oracle ADB Connectivity Check Utility

## Status

Accepted

## Context

Developers need a safe and repeatable way to validate that the local ADB credentials and wallet configuration can establish a database session before implementing LangGraph checkpoint persistence.

## Scope

Provide a command-line utility that reads local credentials from `.env`, opens an Oracle Autonomous Database connection using the configured wallet, validates the session, and reports a clear outcome. This utility does not create checkpoint tables or alter database data.

## Configuration

The utility must read these required variables from the repository-root `.env` file:

| Variable | Purpose |
| --- | --- |
| `DB_USER` | Oracle database user name. |
| `DB_PWD` | Password for `DB_USER`. |
| `WALLET_DIR` | Path to the extracted Oracle ADB wallet directory. |
| `WALLET_PWD` | Password assigned when the wallet was downloaded. |
| `DB_DSN` | ADB service alias or connection string. |

`WALLET_DIR` must be supplied to the driver as both `config_dir` and `wallet_location`.

## Behaviour

1. The implementation must live in `utils/test_db_connection.py`.
2. A thin root-level module named `test_db_connection.py` must delegate to the utility so the command `python -m test_db_connection` works from the repository root.
3. The utility must load the repository-root `.env` file, validate all required variables, and never print their values.
4. It must call `oracledb.connect()` using `DB_USER`, `DB_PWD`, `DB_DSN`, `WALLET_DIR`, and `WALLET_PWD`.
5. After opening a connection, it must execute `SELECT 1 FROM dual` to confirm the session is usable, then close the connection.
6. On success it must print an unambiguous ADB connection success message and exit with status `0`.
7. On missing configuration it must print the names of missing variables, without values, and exit with status `2`.
8. On connection or validation failure it must print a clear error message without credentials and exit with status `1`.

## Acceptance Criteria

* `python -m test_db_connection` resolves the root-level entry point when run from the repository root.
* A valid mocked connection causes a `SELECT 1 FROM dual` execution, a close operation, a success message, and status `0`.
* Missing variables result in status `2` and identify only the variable names.
* A mocked Oracle connection error results in status `1`, a clear failure message, and no secret value in output.
* Unit tests run without a live OCI or ADB connection.

## Out of Scope

* Creating or migrating ADB schema objects.
* Configuring a LangGraph `OracleSaver` or `AsyncOracleSaver`.
* Validating a real database connection as part of automated tests.
