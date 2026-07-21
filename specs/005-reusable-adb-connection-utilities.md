# Specification: Reusable ADB Connection Utilities

## Status

Accepted

## Context

The initial ADB connectivity check introduced configuration types and dotenv loading in `utils/test_db_connection.py`. As examples are added, importing reusable application logic from a command-oriented test utility would create an unclear dependency direction.

## Requirements

1. The repository must provide a neutral utility module at `utils/adb_connection.py`.
2. The module must own the reusable ADB connection boundary:
   * required environment variable names;
   * repository-root `.env` location;
   * `ADBConnectionConfig`;
   * `ConnectionConfigurationError`;
   * loading and validating local connection configuration;
   * safe formatting of non-sensitive connection details; and
   * creation of a wallet-based `oracledb` connection.
3. `utils/test_db_connection.py` must only implement connectivity-check behaviour and import the shared configuration and connection factory from `utils.adb_connection`.
4. `examples/example01/run.py` must import the shared configuration, error type, connection factory, and loader from `utils.adb_connection`. It must not import from `utils.test_db_connection`.
5. Existing command-line behaviour, ADB connection arguments, exit codes, safe output, and unit-test coverage must remain unchanged.
6. Reusable utilities must not execute database operations at import time and must never log or format `DB_PWD` or `WALLET_PWD`.

## Acceptance Criteria

* No example or reusable utility imports from `utils.test_db_connection`; the root-level command entry point and its unit tests may import the command module.
* Both the connectivity utility and Example 01 import shared ADB concerns from `utils.adb_connection`.
* The shared connection factory passes `WALLET_DIR` as both `config_dir` and `wallet_location`.
* All unit tests run without OCI or ADB access and continue to pass.
