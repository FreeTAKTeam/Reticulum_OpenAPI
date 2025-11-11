# FastAPI Integration Helpers

The `reticulum_openapi.integrations.fastapi` package centralises shared
infrastructure for building LXMF-aware FastAPI applications. It provides
configuration models, lifecycle management utilities, reusable command execution
helpers, and diagnostics that were previously embedded inside the Emergency
Management example services.

## Configuration Settings

Use `LXMFClientSettings` together with `create_settings_loader` (or
`load_lxmf_client_settings`) to populate LXMF client configuration from JSON
files or environment variables. Values mirror the historical
`north_api.config.NorthAPIClientSettings` fields:

```python
from pathlib import Path
from reticulum_openapi.integrations.fastapi import create_settings_loader

loader = create_settings_loader(
    default_path=Path("./client_config.json"),
    env_json_var="NORTH_API_CONFIG_JSON",
    env_path_var="NORTH_API_CONFIG_PATH",
)
settings = loader()
```

All values are normalised (paths are stripped, RPC keys lower-cased) and an
optional `require_server_identity` flag enforces mandatory server identity
configuration when desired.

## Managing LXMF Clients

`LXMFClientManager` wraps client instantiation and lifecycle management. It
produces a singleton LXMF client, handles optional announce broadcasts, and can
attach notification bridges during FastAPI startup/shutdown events:

```python
from fastapi import FastAPI
from reticulum_openapi.integrations.fastapi import LXMFClientManager
from reticulum_openapi.integrations.fastapi import LXMFClientSettings

settings = LXMFClientSettings(server_identity_hash="001122...")
manager = LXMFClientManager(lambda: settings)
app = FastAPI()
manager.register_events(app)
```

The manager exposes `get_client()` for dependency injection and
`get_server_identity()` for resolving default server targets. The Emergency
Management northbound API now consumes this helper directly.

## Link Management and Interface Status

`LinkManager` tracks LXMF link attempts, retries connections with backoff, and
records structured status suitable for status endpoints. Applications can start
or stop the retry loop during FastAPI lifecycle events, and the resulting
`LinkStatus` model integrates with diagnostics endpoints. The
`gather_interface_status()` helper inspects active Reticulum interfaces and is
used by the Emergency Management gateway to publish interface metadata.

## Command Execution Contexts

To remove repetitive boilerplate from FastAPI routes, the integration package
introduces `CommandSpec` and `create_command_context_dependency`. A command
context resolves the destination server identity (via query parameter, header,
or configured default), handles dataclass payload preparation, and translates
common LXMF errors into HTTP responses:

```python
from typing import Annotated, Dict
from fastapi import Depends, FastAPI
from reticulum_openapi.integrations.fastapi import (
    CommandSpec,
    LXMFCommandContext,
    LXMFClientManager,
    create_command_context_dependency,
)

manager = LXMFClientManager(loader)
command_specs = {
    "eam:create": CommandSpec(command="CreateEmergencyActionMessage")
}
CommandContext = Annotated[
    LXMFCommandContext,
    Depends(create_command_context_dependency(manager, command_specs)),
]

@app.post("/emergency-action-messages")
async def create_eam(payload: Dict[str, str], context: CommandContext):
    return await context.execute("eam:create", body=payload)
```

Routes simply supply command metadata and optional payload overrides. The
Emergency Management gateway has been refactored to use this shared context for
all LXMF interactions.

## Example Adoption

Both the Emergency Management FastAPI gateway and the northbound API now rely on
`reticulum_openapi.integrations.fastapi` for configuration, dependency
injection, link status tracking, and command execution. Tests under
`tests/integrations/fastapi/` cover the integration points, ensuring lifecycle
hooks and status reporting remain functional across applications.
