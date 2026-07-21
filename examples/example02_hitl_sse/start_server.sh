#!/usr/bin/env sh
# Starts the Example 02 FastAPI development server with the configured port.

set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
environment_file="$repository_root/.env"
default_port=8080

if [ -f "$environment_file" ]; then
    server_port=$(sed -n 's/^SERVER_PORT=//p' "$environment_file" | tail -n 1)
else
    server_port=""
fi

server_port=${server_port:-$default_port}

case "$server_port" in
    *[!0-9]* | '')
        echo "SERVER_PORT must be a numeric TCP port." >&2
        exit 1
        ;;
esac

if [ "$server_port" -lt 1 ] || [ "$server_port" -gt 65535 ]; then
    echo "SERVER_PORT must be between 1 and 65535." >&2
    exit 1
fi

cd "$repository_root"
exec python -m uvicorn examples.example02_hitl_sse.app:app \
    --host 127.0.0.1 \
    --port "$server_port" \
    --reload
