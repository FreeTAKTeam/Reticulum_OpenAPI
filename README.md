# Reticulum OpenAPI

Reticulum OpenAPI is an experimental framework for building lightweight APIs on top of the Reticulum mesh network using LXMF messages. It allows you to expose simple command based or REST style services that work in delay tolerant and very low bandwidth environments.

This repository contains the Python implementation of the framework as well as documentation, a full featured example and generator templates. The goal is to provide an easy way to build applications that communicate over Reticulum using structured messages.

See [docs/protocol_design.md](docs/protocol_design.md) for the protocol overview and [docs/Framework_design.md](docs/Framework_design.md) for architectural details.

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

Before running tests or any of the example programs, make sure the project
dependencies are installed:

```bash
pip install -r requirements.txt
```

Tests can then be run with `pytest` and code style is checked with `flake8`.

## Further resources

- [examples/EmergencyManagement/README.md](examples/EmergencyManagement/README.md) – walkthrough of the sample API implementation.
- [templates/README.md](templates/README.md) – using the generator templates to scaffold a service.
- [docs/Framework_design.md](docs/Framework_design.md) – in-depth description of the architecture.
- [docs/protocol_design.md](docs/protocol_design.md) – detailed protocol design discussion.
