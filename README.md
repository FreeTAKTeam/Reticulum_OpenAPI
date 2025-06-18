# Reticulum OpenAPI

Reticulum OpenAPI is an experimental framework for building lightweight APIs on top of the Reticulum mesh network using LXMF messages. It allows you to expose simple command based or REST style services that work in delay tolerant and very low bandwidth environments.

See [docs/protocol_design.md](docs/protocol_design.md) for the full protocol design discussion.

## Quick start

Install dependencies (requires Python 3.8+):

```bash
pip install -r requirements.txt
```

### Running the example server

```bash
python examples/EmergencyManagement/Server/server_emergency.py
```

### Running the example client

```bash
python examples/EmergencyManagement/client/client_emergency.py
```

The client will ask for the server identity hash which the server prints on startup.

## Development

Tests can be run with `pytest` and code style is checked with `flake8`.
