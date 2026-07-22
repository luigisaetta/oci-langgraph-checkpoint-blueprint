# Specification: Project Documentation Structure

## Status

Accepted

## Context

The repository now includes an executable ADB connectivity utility and a defined Conda environment. The main README should remain focused on project purpose, while setup and first-run instructions need a concise, discoverable location. Significant repository changes also need a permanent history.

## Requirements

1. The repository must include a root-level `CHANGELOG.md` using the Keep a Changelog structure.
2. `CHANGELOG.md` must record the features introduced to date: the project governance guidance, the reproducible Conda environment, secure local ADB configuration, the Oracle ADB connectivity utility, and its safe diagnostic output.
3. Future significant features, fixes, refactorings, specifications, deployment changes, documentation updates, and test-strategy changes must be recorded in `CHANGELOG.md`.
4. The repository must include a root-level `QUICKSTART.md` containing:
   * How to create and activate the `oci-langgraph-checkpoint-blueprint` Conda environment.
   * How an ADB administrator creates a dedicated checkpoint schema owner, with the `CREATE SESSION`, `CREATE TABLE`, and `CREATE INDEX` privileges and a `DATA` tablespace quota required by `OracleSaver.setup()`.
   * How to copy and populate `.env` from `.env.sample` without committing credentials.
   * How to run `python -m test_db_connection` from the repository root and interpret its outcome.
5. The main `README.md` must link to `QUICKSTART.md` and must not duplicate the detailed Conda setup or ADB connectivity-test instructions.
6. The main `README.md` must display badges for Black, Pylint, pytest, Python 3.11+, and spec-driven development. Each badge must link to its relevant tool or repository documentation.
7. The main `README.md` must include an examples table. Each row must link to the example documentation and give a concise explanation of the checkpointing pattern it demonstrates.

## Acceptance Criteria

* `CHANGELOG.md` exists and contains entries for all features introduced before this specification.
* `QUICKSTART.md` contains a runnable Conda creation command, the documented dedicated ADB checkpoint-schema-owner setup before the local connection configuration, and the ADB connectivity test command.
* `README.md` has a prominent Quick Start link and retains no duplicated detailed instructions for those two workflows.
* `README.md` displays all five required badges below its title.
* `README.md` presents available examples in a table with a link and concise summary for each one.
* Documentation never includes ADB passwords, wallet contents, or environment-specific credential values.
