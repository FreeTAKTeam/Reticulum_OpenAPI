# Using OpenAPI with Reticulum OpenAPI (LXMF -> FastAPI + WebSocket)

This repository supports an **OpenAPI-first** workflow for building a Reticulum-backed application and exposing it to a **northbound HTTP API** (FastAPI), with **real-time updates** (SSE today, WebSocket as a small extension).

Reference implementation (recommended to read alongside this doc):

- OpenAPI contract: `examples/EmergencyManagement/API/EmergencyActionMessageManagement-OAS.yaml`
- Mesh service: `examples/EmergencyManagement/Server/server_emergency.py`
- FastAPI gateway: `examples/EmergencyManagement/web_gateway/app.py`
- FastAPI helpers: `docs/fastapi_integration.md`
- Generator templates: `templates/README.md`

## High-level idea

1. Start with an OpenAPI definition (`.yaml`) to describe schemas and operations.
2. Generate a service/client scaffold from the OpenAPI contract.
3. Implement mesh-side handlers (controllers) and register them as commands.
4. Build a FastAPI gateway that maps HTTP routes -> mesh commands and returns JSON.
5. Relay unsolicited mesh notifications northbound via SSE and/or WebSocket.

### Mapping rule: `operationId` -> mesh command

In this project, an OpenAPI `operationId` typically becomes the **command name** registered on the mesh service and invoked from the gateway.

Example (EmergencyManagement):

- OpenAPI `operationId`: `CreateEvent`
- Service registers: `self.add_route("CreateEvent", ...)`
- Gateway executes: `client.send_command(server_identity_hash, "CreateEvent", ...)`

Transport note:

- `reticulum_openapi.client.LXMFClient.send_command()` issues a **Reticulum Link request** to the service's link destination at `"/commands/<operationId>"`.
- Unsolicited events/notifications are typically sent as **LXMF messages** (and are what the built-in SSE bridge relays).

## Prerequisites

Inside this repo:

```bash
pip install -r requirements.txt
```

For contract-first scaffolding:

```bash
pip install openapi-generator-cli
```

For running FastAPI apps:

```bash
pip install uvicorn
```

## Step 1: Write your OpenAPI definition

Create an OpenAPI 3.x YAML that defines:

- `components.schemas`: your request/response payloads (these become dataclasses in generated code)
- `paths` + operations: each operation must have a stable `operationId`

Guidelines that fit the framework well:

- Use short, stable `operationId`s (PascalCase is common here: `CreateThing`, `ListThing`, `RetrieveThing`).
- Prefer object schemas for request bodies so they map cleanly to dataclasses.
- For endpoints with path params (eg `/{id}`), decide how you want to send that identifier over the mesh:
  - Option A (common): include the identifier field on the request dataclass and inject it from the FastAPI path param.
  - Option B: treat the identifier itself as the entire command payload (eg the payload is the string `id`).

WebSocket note:

- OpenAPI 3.x does not natively model WebSocket semantics. If you need a formal socket contract, consider AsyncAPI or document the socket endpoint separately (or via a custom `x-...` extension).

## Step 2: Generate a mesh service + client scaffold

Use the repository templates with `openapi-generator-cli`:

```bash
openapi-generator-cli generate \
  -g python \
  -i path/to/your-api.yaml \
  -t templates \
  -o generated
```

The output includes:

- `models.py`: dataclasses for OpenAPI schemas (based on `reticulum_openapi.model.BaseModel`)
- `controllers.py`: controller skeletons (methods named after `operationId`)
- `service.py`: an `LXMFService` subclass registering each `operationId`
- `server.py`: minimal entrypoint
- `client.py`: minimal client example using `reticulum_openapi.client.LXMFClient`

Tip: if your OpenAPI file contains gateway-only endpoints (eg `/notifications/stream`), you may want to keep a separate "mesh operations" spec for code generation, or delete the generated mesh-side command stubs for those operations after generation.

## Step 3: Implement the mesh service (southbound)

### Register commands (service layer)

Your generated service is an `LXMFService` subclass that registers each operation:

- `self.add_route("<operationId>", controller.<operationId>, payload_type=...)`

When a request arrives, `LXMFService` will:

- decode MessagePack (preferred) or JSON (fallback) into `payload_type` (when provided)
- execute the controller coroutine
- encode the response back to MessagePack (or JSON fallback)

### Implement logic (controller layer)

The generated controller methods are the place to:

- validate / normalise input
- call domain logic and persistence
- return a dataclass, list of dataclasses, dict, primitive, or bytes

### Optional: auth token

Both ends support a simple shared `auth_token`:

- `LXMFClient` injects `auth_token` into dict-like payloads
- `LXMFService` rejects payloads missing/mismatching `auth_token`

### Optional: push notifications to the gateway

To push updates to a known recipient (eg the gateway identity), use:

- `await LXMFService.send_message(<dest_hex>, <title>, <payload>, propagate=<bool>)`

Those unsolicited LXMF messages can then be relayed northbound via SSE/WebSocket (Step 5).

## Step 4: Expose northbound HTTP with FastAPI (gateway)

Use the integration helpers under `reticulum_openapi.integrations.fastapi` to standardise configuration and command dispatch.

### 4.1 Load LXMF client settings

```python
from pathlib import Path

from reticulum_openapi.integrations.fastapi import create_settings_loader
from reticulum_openapi.integrations.fastapi import LXMFClientManager

loader = create_settings_loader(
    default_path=Path("./client_config.json"),
    env_json_var="NORTH_API_CONFIG_JSON",
    env_path_var="NORTH_API_CONFIG_PATH",
)
manager = LXMFClientManager(loader)
```

Settings fields come from `LXMFClientSettings`:

- `server_identity_hash`
- `client_display_name`
- `request_timeout_seconds`
- `lxmf_config_path`
- `lxmf_storage_path`
- `shared_instance_rpc_key`

### 4.2 Define a command map (HTTP key -> mesh command)

```python
from typing import List
from typing import Optional

from reticulum_openapi.integrations.fastapi import CommandSpec
from your_generated.models import Thing  # dataclass generated from OpenAPI

COMMAND_SPECS = {
    "thing:create": CommandSpec(command="CreateThing", request_type=Thing, response_type=Thing),
    "thing:update": CommandSpec(command="PutThing", request_type=Thing, response_type=Optional[Thing]),
    "thing:list": CommandSpec(command="ListThing", response_type=List[Thing]),
}
```

When `request_type` is provided, the gateway builds a dataclass instance from the HTTP body and can inject FastAPI path params via `path_params`.

### 4.3 Add FastAPI endpoints that execute commands

```python
from typing import Annotated, Any, Dict

from fastapi import Depends, FastAPI

from reticulum_openapi.integrations.fastapi import LXMFCommandContext
from reticulum_openapi.integrations.fastapi import create_command_context_dependency

app = FastAPI()

CommandContext = Annotated[
    LXMFCommandContext,
    Depends(create_command_context_dependency(manager, COMMAND_SPECS)),
]

@app.post("/things")
async def create_thing(payload: Dict[str, Any], context: CommandContext):
    return await context.execute("thing:create", body=payload)

@app.put("/things/{thing_id}")
async def put_thing(thing_id: str, payload: Dict[str, Any], context: CommandContext):
    return await context.execute("thing:update", body=payload, path_params={"id": thing_id})
```

Identity routing rules:

- request can target a server via `server_identity` (query) or `X-Server-Identity` (header)
- otherwise the configured `server_identity_hash` is used

## Step 5: Real-time updates (SSE today, WebSocket option)

### 5.1 Built-in SSE bridge

The framework includes an SSE router at `reticulum_openapi.api.notifications`:

- endpoint: `GET /notifications/stream`
- output: SSE frames where `data:` is a JSON document containing:
  - `title`
  - `payload` (decoded MessagePack when possible)
  - `payload_raw` (base64 of the raw payload)

To enable it:

```python
from reticulum_openapi.api.notifications import attach_client_notifications
from reticulum_openapi.api.notifications import router as notifications_router

app.include_router(notifications_router)
manager.register_events(app, attach_notifications=attach_client_notifications)
```

### 5.2 WebSocket relay (pattern)

There is no dedicated WebSocket router shipped today, but you can reuse the same `NotificationHub` as SSE:

```python
from fastapi import WebSocket, WebSocketDisconnect

from reticulum_openapi.api.notifications import notification_hub

@app.websocket("/notifications/ws")
async def notifications_ws(websocket: WebSocket):
    await websocket.accept()
    queue = await notification_hub.add_subscriber()
    try:
        while True:
            message = await queue.get()  # JSON text
            await websocket.send_text(message)
    except WebSocketDisconnect:
        pass
    finally:
        await notification_hub.remove_subscriber(queue)
```

## Step 6: Run the stack

1. Start your mesh service (it prints its identity hash at startup).
2. Put that hash into your gateway config (eg `client_config.json`).
3. Run the FastAPI gateway:

```bash
uvicorn path.to.your_gateway:app --host 0.0.0.0 --port 8000 --reload
```

Then:

- REST docs: `http://localhost:8000/docs`
- SSE stream: `http://localhost:8000/notifications/stream`
- WebSocket (if added): `ws://localhost:8000/notifications/ws`
