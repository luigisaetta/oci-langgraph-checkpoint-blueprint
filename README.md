# OCI LangGraph Checkpoint Blueprint

[![Code style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://pylint.readthedocs.io/)
[![Tests: pytest](https://img.shields.io/badge/tests-pytest-0A9EDC)](https://docs.pytest.org/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Development: Spec-driven](https://img.shields.io/badge/development-spec--driven-6E40C9)](specs/)

**Turn an agent run into a durable business process.**

This repository is a practical blueprint for building enterprise-grade LangGraph workflows and agents whose state survives beyond a single process or request. The demo explores how to persist LangGraph checkpoints in **Oracle Autonomous Database (Oracle ADB)** on Oracle Cloud Infrastructure (OCI).

Instead of treating an agent interaction as an ephemeral chain of calls, the blueprint treats it as a workflow that can be inspected, paused, resumed, and recovered. This is a key step in moving from an interesting agent prototype to a dependable enterprise capability.

## Why checkpoints matter

Enterprise workflows often span more than one model call. They may wait for a person, invoke a tool, encounter a transient failure, or need to continue after a deployment or service restart. Without durable state, that work is lost or difficult to reconstruct.

LangGraph checkpoints provide the state-management foundation for these scenarios. Persisting them in Oracle ADB aims to make the workflow state durable and available through a database platform suited to enterprise operations.

## What this blueprint demonstrates

The project will provide a focused, end-to-end demo of:

* Building a stateful workflow or agent with LangGraph.
* Creating and saving checkpoints as the graph progresses.
* Persisting checkpoint data in Oracle ADB.
* Resuming a workflow from its saved state after interruption.
* Keeping independent workflow threads isolated.
* Testing the LangGraph and database integration boundaries without requiring live OCI resources for unit tests.

## The idea in one picture

```text
User or application request
          |
          v
  LangGraph workflow / agent
          |
          +--> graph state and execution progress
                         |
                         v
        Oracle ADB checkpoint persistence
                         |
                         v
  Resume, recover, inspect, or continue later
```

## Intended audience

This blueprint is for developers, architects, and platform teams who want to understand how durable agent execution can fit into an OCI-based enterprise architecture. It is deliberately centred on the checkpointing pattern rather than on a broad, generic agent platform.

## Project status

The repository is being developed using a spec-driven workflow. Each significant capability will be specified under `specs/` before implementation, with clear acceptance criteria and accompanying tests.

## Quick start

For the complete local setup, including Conda environment creation and the ADB connectivity test, see [QUICKSTART.md](QUICKSTART.md).

Setup instructions, configuration requirements, runnable examples, and OCI deployment guidance will be added alongside the corresponding implementation.

## Design principles

* **Durable by design** — workflow state must be able to outlive a process.
* **Explicit behaviour** — graph state, checkpoint configuration, and persistence semantics are documented and testable.
* **Enterprise boundaries** — OCI and Oracle ADB integration stay separate from core workflow logic where practical.
* **Safe configuration** — credentials and environment-specific values are never committed; configuration uses documented environment variables or safe placeholders.
* **Readable examples** — the demo favours clear, maintainable code over hidden framework magic.

## Contributing

Before implementing a significant change, read the repository’s [AGENTS.md](AGENTS.md). It defines the spec-driven workflow, quality checks, Python conventions, testing expectations, and security rules for this blueprint.
