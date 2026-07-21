# Specification: Development Environment and Initial Dependencies

## Status

Accepted

## Context

This blueprint will demonstrate durable LangGraph workflows and agents whose checkpoints are persisted in Oracle Autonomous Database (ADB). Contributors need one reproducible local Python environment containing only the dependencies required to begin this work and to validate it.

## Scope

This specification defines the initial Conda environment, its dependency groups, and the handling of local ADB credentials. It does not define the checkpoint schema, database implementation, model provider, deployment topology, or a runnable workflow; those require separate specifications.

## Requirements

1. The project must provide an `environment.yml` definition for a Conda environment named `oci-langgraph-checkpoint-blueprint`.
2. The environment must use Python 3.11 and include `pip`.
3. The runtime dependencies must include:
   * `langgraph` for graph and checkpoint abstractions.
   * `langgraph-oracledb` for the Oracle ADB-backed LangGraph checkpoint saver. This project must use the integration documented in Oracle's [`oracle/langchain-oracle`](https://github.com/oracle/langchain-oracle) repository as its primary reference.
   * `oracledb` for Oracle ADB connectivity.
   * `python-dotenv` for explicitly loading local environment configuration.
4. The development dependencies must include `pytest`, `pytest-cov`, `black`, and `pylint`, in line with the repository quality policy.
5. No model-provider SDK, web framework, or LangChain integration may be included in this initial environment. Those dependencies must be justified by a later feature specification.
6. `.env` and local ADB wallet material must remain untracked by Git. `.env.sample` must remain the safe, committed configuration template.

## Acceptance Criteria

* `conda env create --file environment.yml` can create the named environment when package channels are available.
* `conda run --name oci-langgraph-checkpoint-blueprint python --version` reports a Python 3.11 runtime.
* The runtime and development dependency names listed above are present in `environment.yml`.
* `git check-ignore .env wallet_dir/cwallet.sso` confirms that both local credential locations are ignored.
* No credentials, wallet files, DSNs, or environment-specific identifiers are added to version control.

## Integration Contract

The checkpoint implementation must use the Oracle package namespace:

```python
from langgraph_oracledb.checkpoint.oracle import AsyncOracleSaver, OracleSaver
```

The detailed saver configuration and database schema requirements will be specified before the first checkpoint implementation.

## Validation

Validate the definition by creating or updating the Conda environment, importing the runtime libraries, and running the relevant test and quality commands once source code is introduced.
