# Emergency Management Example

This directory contains a minimal example built with **Reticulum OpenAPI**. It demonstrates how to define an API using an OpenAPI specification and expose it over the Reticulum mesh network.

The example models an emergency management system with two main resources:

* **EmergencyActionMessage** – a status report for a callsign
* **Event** – a wrapper that may contain one or more emergency action messages

The dataclass models treat `callsign` (for EmergencyActionMessage) and `uid`
(for Event) as **required** fields. All other properties are optional and may be
omitted or `null` when encoding the JSON payload.

The API contract is described in [`API/EmergencyActionMessageManagement-OAS.yaml`](API/EmergencyActionMessageManagement-OAS.yaml).

## Components

``` mermaid
sequenceDiagram
autonumber
participant ClientApp as Emergency Client (client_emergency.py)
participant ApiClient as LXMFClient
participant Codec as MsgPackCodec
participant LXMF as LXMFTransport
participant ServerApp as Emergency Server (server_emergency.py)
participant Service as EmergencyService (LXMFService)
participant EmergencyCtrl as EmergencyController
participant EventCtrl as EventController

note over ServerApp: On start, prints its identity hash (client needs it)

ClientApp->>ApiClient: init(server_hash)
ApiClient->>Codec: encode(emergency_payload)
Codec-->>ApiClient: bytes
ApiClient->>LXMF: send(to=server_hash, content=bytes)
LXMF-->>ServerApp: deliver(envelope)

ServerApp->>Service: on_message(envelope)
Service->>Codec: decode(bytes)
Codec-->>Service: obj
Service->>EmergencyCtrl: invoke "CreateEmergencyActionMessage"
EmergencyCtrl-->>Service: ack {id, status}

Service->>EventCtrl: invoke event commands
EventCtrl-->>Service: ack/list/data

Service->>Codec: encode(response)
Codec-->>Service: bytes
Service->>LXMF: reply(to=client_hash, content=bytes)
LXMF-->>ClientApp: deliver(reply)

ClientApp->>ApiClient: receive(reply)
ApiClient->>Codec: decode(bytes)
Codec-->>ApiClient: ack/status
ApiClient-->>ClientApp: display result
```

The `LXMFClient` in `client_emergency.py` wraps the MessagePack codec used by
the SDK, so the client code can hand off dataclasses directly when calling
`send_command`. On the server side, `server_emergency.py` instantiates the
`EmergencyService` (a subclass of `LXMFService` defined in
`service_emergency.py`). That service decodes the payload, resolves the matching
route, and invokes the controller registered for the command (either
`EmergencyController` or `EventController`) before packaging the response for
the client.

| Folder | Description |
|-------|-------------|
| `Server/` | Asynchronous service implementation. Defines dataclasses, controllers, a small SQLite database and the service class. |
| `client/` | Simple client that connects to the server, creates a message and then retrieves it back to demonstrate persistence. |
| `API/` | OpenAPI specification for the example. |

### Server
- `models_emergency.py` – dataclass models for the API payloads.
- `controllers_emergency.py` – async handlers for API commands.
- `database.py` – initializes a small SQLite database used for persistence.
- `service_emergency.py` – subclass of `LXMFService` that registers the routes.
- `server_emergency.py` – starts the service, announces its identity and keeps running until interrupted (e.g. with Ctrl+C).

### Client
- `client_emergency.py` – reuses a stored server identity hash when available and otherwise prompts before sending a sample request using `LXMFClient`.

## Running the example

1. Install the project dependencies from the repository root:

```bash
pip install -r requirements.txt
```

2. Start the server in one terminal:

```bash
python Server/server_emergency.py
```

   The server prints its identity hash on startup. Keep this hash handy.
   Leave the server running until you are done experimenting, then press
   `Ctrl+C` (or send `SIGTERM`) to stop it gracefully.

   Optionally, save the hash in `client/client_config.json` so the client can reuse it automatically:

   ```json
   {
     "server_identity_hash": "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
   }
   ```

3. In another terminal, run the client. It will reuse the stored hash when available or prompt you for one:

```bash
python client/client_emergency.py
```

The client first sends a `CreateEmergencyActionMessage` request and prints the
response returned by the server. It then issues a `RetrieveEmergencyActionMessage`
command for the same callsign and displays the stored record, demonstrating that
the data is persisted in `emergency.db`.

This example assumes a working Reticulum environment. When running on separate machines, ensure that both client and server can communicate over the Reticulum network.
