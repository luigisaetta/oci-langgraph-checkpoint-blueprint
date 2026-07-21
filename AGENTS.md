# AGENTS.md

This repository contains a blueprint and implementation guidance for building enterprise-grade LangGraph workflows and agents on Oracle Cloud Infrastructure (OCI), using checkpoints persisted in Oracle Autonomous Database (Oracle ADB).

## Repository purpose

Keep the repository focused on one goal: demonstrate how LangGraph checkpoints enable durable, resumable enterprise workflows and agents, and how Oracle ADB can persist those checkpoints.

All changes must preserve this purpose. Avoid adding unrelated frameworks, demos, deployment targets, or abstractions unless they are explicitly required by the specification being implemented.

## Language and documentation

* All documentation and Markdown files must be written in English.
* Keep documentation practical and close to the implementation.
* Public behaviour must be documented when it changes.
* Local execution instructions and OCI deployment instructions must be updated whenever a feature affects runtime behaviour.

## Spec-driven development workflow

Follow this workflow for significant features, fixes, refactorings, deployment changes, and checkpoint-persistence changes:

1. Read the relevant existing specification.
2. If no relevant specification exists, create one under `specs/` before implementation.
3. Review the specification for scope, behaviour, acceptance criteria, error handling, configuration, and test expectations.
4. Implement code according to the specification.
5. Add or update unit tests.
6. Run the relevant formatting, linting, testing, and coverage checks.
7. Update `CHANGELOG.md` when the change is significant.
8. Summarise what changed and which checks were run.

Code must not be generated for significant behaviour until the relevant specification exists and has clear acceptance criteria.

## Codex working rules

When working in this repository, Codex should:

* Inspect the existing project structure before editing.
* Prefer small, coherent changes over broad rewrites.
* Reuse existing modules, helpers, configuration patterns, and test fixtures before adding new ones.
* Preserve user changes already present in the working tree.
* Avoid speculative changes that are not requested by the user or required by the specification.
* Avoid introducing unrelated abstractions, frameworks, deployment targets, or examples.
* Do not create commits unless explicitly asked.
* Do not add new production dependencies without a clear reason.
* Do not run destructive commands or discard existing changes unless explicitly requested.
* Do not invent details about LangGraph, OCI, Oracle ADB, IAM, networking, checkpoint storage, or deployment behaviour.
* When uncertain, document the assumption, leave a clear TODO, or ask for clarification.

## Python environment

Use the `oci-langgraph-checkpoint-blueprint` Conda environment for local development and tests.

If an environment definition exists, prefer it for setup. If the environment already exists, activate `oci-langgraph-checkpoint-blueprint` before running checks.

Do not assume globally installed Python packages are available.

## Required checks

Run the relevant checks before considering work complete.

At a minimum, use the project standard tools for:

* Python formatting with `black`.
* Python linting with `pylint`.
* Unit testing with `pytest`.
* Coverage reporting when tests or behaviour are affected.

The target unit test coverage is above 80 percent.

If a check cannot be run because the environment or dependencies are missing, state that clearly in the final summary and explain what prevented the check.

## Python code conventions

Every Python source file must start with a multiline header using this format:

```python
"""
Author: L. Saetta
Date last modified: YYYY-MM-DD
License: MIT
Description: Brief description of the responsibilities and functions contained in this file.
"""
```

Use the actual modification date when creating or updating a Python source file.

All generated Python code must include accurate docstrings for modules, classes, methods, and functions where applicable.

Docstrings must follow the Google Python docstring format and clearly describe purpose, arguments, return values, raised exceptions, and relevant side effects.

## Human readability and maintainability

Code generated for this repository must be optimised for human readability first. Prefer clear structure and explicit intent over cleverness, dense abstractions, or overly compact expressions.

* Use descriptive names for modules, classes, functions, methods, variables, and tests.
* Keep functions focused on one clear responsibility.
* Prefer straightforward control flow over deeply nested logic.
* Make error handling explicit and predictable.
* Avoid hidden side effects and implicit global state.
* Keep configuration access centralised and easy to audit.
* Keep OCI and Oracle ADB integration code isolated from core workflow and agent logic where practical.
* Write tests that describe behaviour clearly and can be understood as executable documentation.

## LangGraph checkpoint design expectations

* Keep graph construction, node behaviour, state definitions, checkpoint configuration, and persistence semantics documented in specifications.
* Demonstrate durable execution, recovery or resume behaviour, and thread isolation where relevant.
* Prefer deterministic and testable agent behaviour in examples.
* Keep sample prompts, model settings, and OCI configuration visible and easy to change.
* Define the Oracle ADB persistence boundary explicitly and test it with mocks or fakes.
* Do not hard-code secrets, tenancy-specific identifiers, database connection details, API keys, private endpoints, or local machine paths.
* Provide local execution instructions and OCI deployment instructions whenever a feature affects runtime behaviour.

## OCI configuration and security

Never commit or hard code API keys, private keys, passwords, OCI tenancy OCIDs, user OCIDs, compartment OCIDs, database credentials, private endpoints, local machine paths, or customer- and environment-specific identifiers.

Use environment variables, configuration files excluded from version control, or documented placeholders.

When adding configuration, document its variable name, purpose, whether it is required, a safe example value, and where it is used.

## Testing expectations

New functionality must include unit tests written with the project standard testing framework.

Tests should cover successful workflow and agent paths, validation failures, error handling, checkpoint creation and retrieval, resume behaviour, thread isolation, configuration loading, Oracle ADB integration boundaries using mocks or fakes, and LangGraph node and state behaviour where applicable.

Tests should avoid real OCI or Oracle ADB calls unless explicitly marked as integration tests.

## Dependency policy

Before adding a dependency, check whether the repository already has an equivalent library or helper. Prefer standard-library functionality when practical, add dependencies to the appropriate environment or requirements file, explain why they are needed, and update documentation if setup changes.

Do not introduce new frameworks unless the specification requires them.

## Changelog policy

Update `CHANGELOG.md` when a change is significant, including features, fixes, refactorings, specification updates, deployment changes, documentation updates, and test-strategy changes.

Keep changelog entries concise and understandable.

## Definition of done

A change is done only when:

* The relevant specification has been written or updated.
* The implementation conforms to the specification.
* The relevant formatting, linting, testing, and coverage checks have been considered.
* Unit tests have been written or updated when behaviour changes.
* Documentation has been updated when public behaviour, setup, or deployment changes.
* `CHANGELOG.md` has been updated when required.
* Any inability to run checks has been clearly documented.
