# Emergency Management Northbound Client

This guide explains how the Emergency Management northbound FastAPI gateway, the
shared LXMF client, and the Vite single-page application (SPA) cooperate on top
of the existing LXMF service. It also outlines the configuration knobs required
to run the full stack—LXMF service, FastAPI gateway, and UI—side by side during
local development.

## Component overview

- **LXMF Service (`Server/server_emergency.py`)** – registers LXMF commands for
  emergency action messages and events and persists them in SQLite through the
  controller layer.【F:examples/EmergencyManagement/README.md†L44-L79】
- **Northbound FastAPI gateway (`web_gateway/app.py`)** – exposes REST endpoints
  for the SPA. Each route converts JSON payloads into dataclasses before sending
  the corresponding LXMF command via the shared `LXMFClient` helper and returns
  MessagePack responses as JSON.【F:examples/EmergencyManagement/web_gateway/app.py†L30-L188】
- **LXMF client helper (`client/client.py`)** – wraps send/receive helpers used
  by both the CLI demo and the FastAPI gateway so that dataclasses can be passed
  directly into `send_command`.【F:examples/EmergencyManagement/client/client_emergency.py†L129-L186】
- **SPA (`webui/`)** – React application that consumes the REST gateway through
  a central Axios client and subscribes to live updates via Server-Sent Events
  (SSE).【F:examples/EmergencyManagement/webui/src/lib/apiClient.ts†L53-L110】【F:examples/EmergencyManagement/webui/src/lib/liveUpdates.ts†L1-L109】

The gateway imports `LXMFClient` from the client package, ensuring a single
connection handles all REST requests while reusing the same identity and timeout
configuration validated by the CLI tooling.【F:examples/EmergencyManagement/web_gateway/app.py†L30-L118】

## Configuration

### LXMF client JSON

Both the CLI client and the FastAPI gateway load defaults from
[`client_config.json`](./client_config.json). Populate the following keys with
values suited to your mesh before starting the stack:

| Key | Purpose |
| --- | --- |
| `server_identity_hash` | Destination hash of the running LXMF service. |
| `client_display_name` | Friendly name announced on the mesh. |
| `request_timeout_seconds` | Awaited response timeout for LXMF commands. |
| `lxmf_config_path` | Optional override for the Reticulum configuration path. |
| `lxmf_storage_path` | Optional override for the Reticulum storage directory. |

The FastAPI gateway reads this file during import. You can override it with the
`NORTH_API_CONFIG_PATH` environment variable or provide an entire JSON payload
via `NORTH_API_CONFIG_JSON` when deploying to containerised environments.【F:examples/EmergencyManagement/client/north_api/config.py†L12-L70】

### Gateway identity resolution

The REST gateway attempts to reuse the stored server identity hash. Requests can
also pass `X-Server-Identity` headers or a `server_identity` query parameter to
target different services without restarting the gateway.【F:examples/EmergencyManagement/web_gateway/app.py†L148-L186】

### SPA environment variables

The web UI consumes Vite environment variables to locate the gateway and live
update stream:

| Variable | Description |
| --- | --- |
| `VITE_API_BASE_URL` | Base URL of the FastAPI gateway. |
| `VITE_UPDATES_URL` | Optional SSE endpoint. Defaults to `<base>/notifications/stream`. |
| `VITE_SERVER_IDENTITY` | Optional identity hash forwarded with each request. |

These settings are read when the bundle initializes the Axios client and when it
creates an `EventSource` for real-time updates.【F:examples/EmergencyManagement/webui/src/lib/apiClient.ts†L53-L91】

## Real-time updates

The SPA maintains a singleton `EventSource` that subscribes to the gateway's
stream endpoint (default `/notifications/stream`). Incoming messages are normalised into
resource/action pairs before they trigger React Query cache invalidation. The
utility tolerates reconnection and mixed-content failures to keep the page in
sync even when the SSE channel drops.【F:examples/EmergencyManagement/webui/src/lib/liveUpdates.ts†L19-L109】

To surface updates, configure the FastAPI gateway (or an auxiliary bridge) to
publish JSON events such as:

```json
{
  "resource": "emergency-action-message",
  "action": "updated",
  "payload": { "callsign": "ALPHA", "securityStatus": "Yellow" }
}
```

Any event whose `resource` contains `message` or `event` automatically maps to
the relevant React Query caches, allowing optimistic UI flows to converge with
mesh state once the LXMF service completes a command.【F:examples/EmergencyManagement/webui/src/lib/liveUpdates.ts†L35-L109】

## Running the stack concurrently

1. **Install dependencies** – from the repository root, install Python packages
   and the web UI toolchain:

   ```bash
   pip install -r requirements.txt
   cd examples/EmergencyManagement/webui && npm install
   ```

2. **Start the LXMF service** – in the first terminal, launch the server. It
   announces its identity hash on start-up; copy the hash into
   `client_config.json` for reuse.

   ```bash
   cd examples/EmergencyManagement/Server
   python server_emergency.py
   ```

3. **Run the FastAPI gateway** – in a second terminal, serve the REST API. Pick
   a port that does not conflict with your UI (e.g. `8000`).

   ```bash
   uvicorn examples.EmergencyManagement.web_gateway.app:app --host 0.0.0.0 --port 8000 --reload
   ```

   The gateway enables CORS by default so the Vite UI can call it from
   `http://localhost:5173`. To restrict the allowed origins, set the
   `EMERGENCY_GATEWAY_ALLOWED_ORIGINS` environment variable to a
   comma-separated list before starting Uvicorn (for example,
   `EMERGENCY_GATEWAY_ALLOWED_ORIGINS=http://localhost:5173`).

   The gateway loads the LXMF client singleton during startup and announces it
   on the mesh using the configured display name and identity paths.【F:examples/EmergencyManagement/web_gateway/app.py†L101-L143】

4. **Launch the SPA** – in a third terminal, start the Vite development server.
   Point `VITE_API_BASE_URL` (and optionally `VITE_SERVER_IDENTITY`) at the
   gateway port chosen above.

   ```bash
   cd examples/EmergencyManagement/webui
   VITE_API_BASE_URL=http://localhost:8000 npm run dev
   ```

5. **Optional: expose the northbound health API** – the lightweight
   `north_api` FastAPI package can run alongside the gateway to expose
   deployment health checks and configuration without hitting the REST
   endpoints directly.

   ```bash
   uvicorn examples.EmergencyManagement.client.north_api.app:app --host 0.0.0.0 --port 8100
   ```

   Lifecycle hooks initialise the shared `LXMFClient` once and stop announce
   listeners gracefully during shutdown.【F:examples/EmergencyManagement/client/north_api/dependencies.py†L14-L66】

With all processes running, the SPA issues REST commands to the gateway. Each
request is translated into the appropriate LXMF command, forwarded to the
service, and the resulting MessagePack payload is converted back into JSON for
rendering in the browser.【F:examples/EmergencyManagement/web_gateway/app.py†L30-L188】
