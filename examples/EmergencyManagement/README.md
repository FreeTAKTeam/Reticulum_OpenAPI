# Emergency Management Example

This directory contains a minimal example built with **Reticulum OpenAPI**. It demonstrates how to define an API using an OpenAPI specification and expose it over the Reticulum mesh network.

The example models an emergency management system with two main resources:

* **EmergencyActionMessage** – a status report for a callsign
* **Event** – a wrapper that may contain one or more emergency action messages

The API contract is described in [`API/EmergencyActionMessageManagement-OAS.yaml`](API/EmergencyActionMessageManagement-OAS.yaml).

## Components

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
- `server_emergency.py` – starts the service, announces its identity and runs for ~30 seconds.

### Client
- `client_emergency.py` – prompts for the server identity hash and sends a sample request using `LXMFClient`.

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

3. In another terminal, run the client and enter the identity hash when prompted:

```bash
python client/client_emergency.py
```

The client first sends a `CreateEmergencyActionMessage` request and prints the
response returned by the server. It then issues a `RetrieveEmergencyActionMessage`
command for the same callsign and displays the stored record, demonstrating that
the data is persisted in `emergency.db`.

This example assumes a working Reticulum environment. When running on separate machines, ensure that both client and server can communicate over the Reticulum network.
