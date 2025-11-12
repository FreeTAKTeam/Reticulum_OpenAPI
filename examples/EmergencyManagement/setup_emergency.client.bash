#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: setup_emergency.client.bash [--skip-install]

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

echo "Launching FastAPI gateway in a new terminal window..."
GATEWAY_CMD="cd \"$REPO_ROOT\" && \"$VENV_PYTHON\" -m uvicorn examples.EmergencyManagement.web_gateway.app:app --host 127.0.0.1 --port 8000 --reload"
launch_console "FastAPI Gateway" "$GATEWAY_CMD"

echo "Launching web UI dev server in a new terminal window..."
WEBUI_CMD="cd \"$WEBUI_DIR\" && npm run dev"
launch_console "Web UI Dev Server" "$WEBUI_CMD"

echo "Both services are running in separate consoles. Close their windows or press Ctrl+C inside them to stop the processes."
