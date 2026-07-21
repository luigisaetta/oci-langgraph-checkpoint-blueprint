# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

* Repository governance in `AGENTS.md`, including the spec-driven development workflow, quality expectations, and security rules.
* A reproducible Conda environment for Python 3.11, LangGraph, `langgraph-oracledb`, `oracledb`, and the project quality tools.
* Safe local ADB configuration through `.env.sample`, with `.env` and local wallet material excluded from Git.
* A documented Oracle ADB connection utility, available through `python -m test_db_connection`, with unit tests that do not require OCI resources.
* `QUICKSTART.md` for local environment setup and ADB connection validation.
* This changelog and the documentation-structure specification that governs its ongoing maintenance.
* README badges for Black, Pylint, pytest, Python 3.11+, and the spec-driven development workflow.
* Example 01: a one-node LangGraph flow that persists checkpoints through Oracle ADB with `OracleSaver`.

### Changed

* The ADB connection utility now displays a safe connection summary before reporting the result; database and wallet passwords are never shown.
* The README now links to the dedicated quick start guide instead of duplicating setup and connectivity-test instructions.

## Changelog policy

Add an entry under `Unreleased` for every significant feature, fix, refactoring, specification, deployment change, documentation update, or test-strategy change.
