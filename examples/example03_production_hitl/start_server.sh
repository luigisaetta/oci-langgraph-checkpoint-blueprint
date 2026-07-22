#!/usr/bin/env sh
# Starts the Example 03 FastAPI server with its dedicated configured port.

set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
environment_file="$repository_root/.env"
default_port=8081

if [ -f "$environment_file" ]; then
    server_port=$(/usr/bin/sed -n 's/^EXAMPLE03_SERVER_PORT=//p' "$environment_file" | /usr/bin/tail -n 1)
else
    server_port=""
fi

server_port=${server_port:-$default_port}

case "$server_port" in
    *[!0-9]* | '')
        echo "EXAMPLE03_SERVER_PORT must be a numeric TCP port." >&2
        exit 1
        ;;
esac

if [ "$server_port" -lt 1 ] || [ "$server_port" -gt 65535 ]; then
    echo "EXAMPLE03_SERVER_PORT must be between 1 and 65535." >&2
    exit 1
fi

cd "$repository_root"
exec python -m uvicorn examples.example03_production_hitl.app:app \
    --host 127.0.0.1 \
    --port "$server_port" \
    --reload
