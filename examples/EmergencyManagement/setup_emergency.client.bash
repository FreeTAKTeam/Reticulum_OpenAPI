#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: setup_emergency.client.bash [--skip-install]

Install dependencies (unless --skip-install) and launch:
  • FastAPI gateway (uvicorn)
  • Emergency Management web UI (Vite dev server)

Use Ctrl+C to stop both processes.
EOF
}

require_cmd() {
    local cmd="$1"
    local label="${2:-$cmd}"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Error: required command '$label' not found on PATH." >&2
        exit 1
    fi
}

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
WEBUI_DIR="$SCRIPT_DIR/webui"
REQUIREMENTS_FILE="$REPO_ROOT/requirements.txt"
ENV_EXAMPLE="$WEBUI_DIR/.env.example"
ENV_FILE="$WEBUI_DIR/.env"

SKIP_INSTALL=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-install)
            SKIP_INSTALL=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

echo "Repository root: $REPO_ROOT"

require_cmd python3 "Python 3"
require_cmd npm "npm"

if [[ $SKIP_INSTALL -eq 0 ]]; then
    echo "Installing Python dependencies..."
    python3 -m pip install --upgrade pip
    python3 -m pip install -r "$REQUIREMENTS_FILE"

    echo "Installing web UI dependencies (npm install)..."
    (cd "$WEBUI_DIR" && npm install)
else
    echo "Skipping dependency installation (--skip-install supplied)."
fi

if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$ENV_EXAMPLE" ]]; then
        echo "Creating default webui/.env configuration..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
    else
        echo "Warning: $ENV_EXAMPLE not found; skipping .env creation." >&2
    fi
else
    echo "webui/.env already exists; leaving it untouched."
fi

PIDS=()

cleanup() {
    echo "Stopping background processes..."
    for pid in "${PIDS[@]:-}"; do
        if kill -0 "$pid" >/dev/null 2>&1; then
            kill "$pid" >/dev/null 2>&1 || true
        fi
    done
}
trap cleanup INT TERM EXIT

echo "Starting FastAPI gateway..."
(
    cd "$REPO_ROOT"
    exec python3 -m uvicorn examples.EmergencyManagement.web_gateway.app:app \
        --host 127.0.0.1 --port 8000 --reload
) &
PIDS+=($!)

echo "Starting web UI dev server..."
(
    cd "$WEBUI_DIR"
    exec npm run dev
) &
PIDS+=($!)

echo "FastAPI gateway PID: ${PIDS[0]}"
echo "Web UI dev server PID: ${PIDS[1]}"
echo "Press Ctrl+C to stop both services."

wait
