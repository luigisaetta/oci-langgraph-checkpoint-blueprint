# Quick Start

This guide gets a local development environment ready and verifies access to Oracle Autonomous Database (ADB).

## Prerequisites

* Conda installed and available on the command line.
* An extracted ADB wallet available only on the local machine.
* A database user, its password, the wallet password, and an ADB service alias or connection string.

## Create the Conda environment

From the repository root, create and activate the project environment:

```bash
conda env create --file environment.yml
conda activate oci-langgraph-checkpoint-blueprint
```

If the environment already exists, update it from the declared dependencies:

```bash
conda env update --name oci-langgraph-checkpoint-blueprint --file environment.yml
```

The environment includes LangGraph, `langgraph-oracledb`, the Oracle Python driver, FastAPI, Uvicorn, HTTPX, and the project test and quality tools.

## Configure the local ADB connection

If `.env` does not exist yet, create it from the safe template:

```bash
cp .env.sample .env
```

Fill in these local values in `.env`:

| Variable | Description |
| --- | --- |
| `DB_USER` | Oracle database user name. |
| `DB_PWD` | Password for the database user. |
| `WALLET_DIR` | Path to the extracted ADB wallet directory. |
| `WALLET_PWD` | Password set when the wallet was downloaded. |
| `DB_DSN` | ADB service alias or connection string. |
| `SERVER_PORT` | Local FastAPI port for Example 02. Use `8080` by default. |

Never commit `.env` or the wallet directory. Both are excluded by `.gitignore`.

## Test the ADB connection

With the Conda environment active, run this command from the repository root:

```bash
python -m test_db_connection
```

The utility prints the non-sensitive `DB_USER`, `DB_DSN`, and `WALLET_DIR` values, runs `SELECT 1 FROM dual`, and then reports the outcome. It never prints `DB_PWD` or `WALLET_PWD`.

| Exit code | Meaning |
| --- | --- |
| `0` | ADB connection and validation query succeeded. |
| `1` | The connection or validation query failed. Check the credentials, wallet path, DSN, and network access. |
| `2` | Required values are missing from `.env`. |
