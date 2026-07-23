# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

* Example 04 is now an independent, durable IT procurement agent with an LLM-generated simulated offer and approval workflow, plus its own pooled FastAPI API on port 8082.
* Example 04 now uses OCI Generative AI Responses API calls to extract a strict structured procurement request and generate its simulated offer.
* Example 04: a standalone Next.js browser UI with a streamed event timeline, durable thread reload, approval controls, unit tests, and an operational runbook.
* A root-level `OracleSaver` best-practices guide covering connection pooling, checkpoint-data security, retention, authorization, idempotent side effects, concurrency, operations, and production validation.
* Example 03 now includes a dedicated recovery-demonstration runbook that separates each user action from the expected observable result.
* Example 03: a production-oriented FastAPI HITL service with an ADB connection pool, durable run-status API, sequentially idempotent final decisions, and a client-led server-restart recovery demonstration.
* Example 02 now includes a standalone, code-first guide to Oracle ADB checkpointing and LangGraph Human-in-the-Loop pause and resume patterns, linked to the complete implementation.
* The Quick Start now documents creating a least-privilege ADB checkpoint schema owner before configuring the local connection, including the privileges and tablespace quota required by `OracleSaver.setup()`.
* Repository governance in `AGENTS.md`, including the spec-driven development workflow, quality expectations, and security rules.
* A reproducible Conda environment for Python 3.11, LangGraph, `langgraph-oracledb`, `oracledb`, and the project quality tools.
* Safe local ADB configuration through `.env.sample`, with `.env` and local wallet material excluded from Git.
* A documented Oracle ADB connection utility, available through `python -m test_db_connection`, with unit tests that do not require OCI resources.
* `QUICKSTART.md` for local environment setup and ADB connection validation.
* This changelog and the documentation-structure specification that governs its ongoing maintenance.
* README badges for Black, Pylint, pytest, Python 3.11+, and the spec-driven development workflow.
* Example 01: a one-node LangGraph flow that persists checkpoints through Oracle ADB with `OracleSaver`.
* Example 02: a three-node Human-in-the-Loop LangGraph agent with Oracle ADB checkpoints, FastAPI SSE streaming, and an interactive Python client.

### Changed

* Example 04 has been renamed to `example04_it_procurement` and separated into dedicated `backend/` FastAPI/LangGraph and `frontend/` Next.js directories.
* Example 02 now uses `SERVER_PORT=8080` as its default FastAPI port, with a documented shell script for starting Uvicorn.
* The main README now highlights streamed human approval and resume behaviour, and presents the example catalogue as a linked table with concise descriptions.
* The ADB connection utility now displays a safe connection summary before reporting the result; database and wallet passwords are never shown.
* The README now links to the dedicated quick start guide instead of duplicating setup and connectivity-test instructions.
* Shared ADB configuration and wallet-based connection handling now live in `utils.adb_connection`, separating reusable application concerns from the connectivity-check command.
* Example 01 now generates and displays a unique `example01-` thread ID for every execution.
* Example 01 serializes checkpoint JSON metadata in its documented inspection query for SQL-client compatibility.
* Example 01 now explains the three durable checkpoint snapshots created by one one-node graph execution.
* Example 02 client now separates streamed SSE events with blank lines for readability.
* Example 02 client now starts with a titled safe-configuration header.
* Example 02 now documents how to verify the persisted HITL pause and final decision checkpoint in ADB.
* Example 02 graph nodes are now callable classes, allowing their instances to be registered directly with LangGraph.
* Example 02 client now presents a three-step workflow timeline alongside the detailed SSE event payloads.

## Changelog policy

Add an entry under `Unreleased` for every significant feature, fix, refactoring, specification, deployment change, documentation update, or test-strategy change.
