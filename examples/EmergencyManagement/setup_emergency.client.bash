#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: setup_emergency.client.bash [--skip-install] [--gateway-port PORT] [--gateway-host HOST]

Install dependencies (unless --skip-install), ensure a Python virtual
environment exists, and launch:
  - FastAPI gateway (uvicorn) in its own terminal window
  - Emergency Management web UI (Vite dev server) in its own terminal window

Use Ctrl+C inside each new window or close it to stop the corresponding service.
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

detect_terminal() {
    local candidates=(
        "${TERMINAL_BIN:-}"
        x-terminal-emulator
        gnome-terminal
        xfce4-terminal
        konsole
        mate-terminal
        tilix
        kitty
        alacritty
        lxterminal
        terminator
        xterm
        uxterm
        urxvt
    )
    for term in "${candidates[@]}"; do
        if [[ -n "$term" ]] && command -v "$term" >/dev/null 2>&1; then
            echo "$term"
            return 0
        fi
    done
    return 1
}

launch_console() {
    local title="$1"
    local command="$2"
    local shell_cmd="bash -lc \"$command; exec bash\""
    case "$TERMINAL_BIN" in
        gnome-terminal|mate-terminal|tilix)
            "$TERMINAL_BIN" --title "$title" -- bash -lc "$command; exec bash" &
            ;;
        konsole)
            "$TERMINAL_BIN" --new-window -p tabtitle="$title" -e bash -lc "$command; exec bash" &
            ;;
        xfce4-terminal|lxterminal|terminator)
            "$TERMINAL_BIN" --title "$title" --command="$shell_cmd" &
            ;;
        kitty)
            "$TERMINAL_BIN" --title "$title" bash -lc "$command; exec bash" &
            ;;
        alacritty)
            "$TERMINAL_BIN" --title "$title" -e bash -lc "$command; exec bash" &
            ;;
        xterm|uxterm|urxvt|x-terminal-emulator)
            "$TERMINAL_BIN" -T "$title" -e bash -lc "$command; exec bash" &
            ;;
        *)
            "$TERMINAL_BIN" -e bash -lc "$command; exec bash" &
            ;;
    esac
}

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
WEBUI_DIR="$SCRIPT_DIR/webui"
REQUIREMENTS_FILE="$REPO_ROOT/requirements.txt"
VENV_DIR="$REPO_ROOT/.venv-emergency"
VENV_PYTHON="$VENV_DIR/bin/python"
ENV_EXAMPLE="$WEBUI_DIR/.env.example"
ENV_FILE="$WEBUI_DIR/.env"

SKIP_INSTALL=0
GATEWAY_HOST="127.0.0.1"
GATEWAY_PORT=8000
GATEWAY_PORT_SET=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-install)
            SKIP_INSTALL=1
            shift
            ;;
        --gateway-port)
            if [[ $# -lt 2 ]]; then
                echo "Error: --gateway-port requires a value." >&2
                exit 1
            fi
            if ! [[ "$2" =~ ^[0-9]+$ ]] || (( $2 < 1 || $2 > 65535 )); then
                echo "Error: --gateway-port must be an integer between 1 and 65535." >&2
                exit 1
            fi
            GATEWAY_PORT="$2"
            GATEWAY_PORT_SET=1
            shift 2
            ;;
        --gateway-host)
            if [[ $# -lt 2 ]]; then
                echo "Error: --gateway-host requires a value." >&2
                exit 1
            fi
            GATEWAY_HOST="$2"
            shift 2
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

is_port_available() {
    local host="$1"
    local port="$2"
    python3 - "$host" "$port" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    result = sock.connect_ex((host, port))

sys.exit(0 if result != 0 else 1)
PY
}

find_available_port() {
    local host="$1"
    local start_port="$2"
    local end_port=$((start_port + 50))
    local port=$start_port
    while (( port <= end_port )); do
        if is_port_available "$host" "$port"; then
            echo "$port"
            return 0
        fi
        port=$((port + 1))
    done
    return 1
}

ensure_uvicorn() {
    if [[ -x "$VENV_PYTHON" ]] && "$VENV_PYTHON" -m pip show uvicorn >/dev/null 2>&1; then
        return
    fi
    if [[ $SKIP_INSTALL -eq 1 ]]; then
        echo "Error: uvicorn is not installed in the virtual environment." >&2
        echo "Run the script without --skip-install at least once." >&2
        exit 1
    fi
    echo "Installing uvicorn inside the virtual environment..."
    "$VENV_PYTHON" -m pip install uvicorn
}

TERMINAL_BIN="$(detect_terminal || true)"
if [[ -z "$TERMINAL_BIN" ]]; then
    cat <<'ERR' >&2
Error: no supported terminal emulator was found. Install one (e.g. gnome-terminal,
konsole, xterm) or set TERMINAL_BIN to the command that opens a new terminal window.
ERR
    exit 1
fi
echo "Using terminal emulator: $TERMINAL_BIN"

if [[ $SKIP_INSTALL -eq 0 ]]; then
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "Creating Python virtual environment at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
    fi
    echo "Installing Python dependencies inside the virtual environment..."
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE"
    ensure_uvicorn

    echo "Installing web UI dependencies (npm install)..."
    (cd "$WEBUI_DIR" && npm install)
else
    if [[ ! -x "$VENV_PYTHON" ]]; then
        echo "Error: virtual environment not found at $VENV_DIR." >&2
        echo "Run the script without --skip-install at least once to create it." >&2
        exit 1
    fi
    ensure_uvicorn
    echo "Skipping dependency installation (--skip-install supplied)."
fi

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Error: expected Python virtual environment missing at $VENV_DIR." >&2
    exit 1
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

if ! is_port_available "$GATEWAY_HOST" "$GATEWAY_PORT"; then
    if [[ $GATEWAY_PORT_SET -eq 1 ]]; then
        echo "Error: specified gateway port $GATEWAY_PORT on host $GATEWAY_HOST is already in use." >&2
        exit 1
    fi
    if NEW_PORT=$(find_available_port "$GATEWAY_HOST" "$GATEWAY_PORT"); then
        echo "Port $GATEWAY_PORT is busy; using available port $NEW_PORT instead."
        GATEWAY_PORT="$NEW_PORT"
    else
        echo "Error: could not find a free port near $GATEWAY_PORT for the FastAPI gateway." >&2
        exit 1
    fi
fi

echo "Launching FastAPI gateway in a new terminal window..."
GATEWAY_CMD="cd \"$REPO_ROOT\" && \"$VENV_PYTHON\" -m uvicorn examples.EmergencyManagement.web_gateway.app:app --host \"$GATEWAY_HOST\" --port \"$GATEWAY_PORT\" --reload"
launch_console "FastAPI Gateway" "$GATEWAY_CMD"

echo "Launching web UI dev server in a new terminal window..."
WEBUI_CMD="cd \"$WEBUI_DIR\" && npm run dev"
launch_console "Web UI Dev Server" "$WEBUI_CMD"

echo "Both services are running in separate consoles. Close their windows or press Ctrl+C inside them to stop the processes."
