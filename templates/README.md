# Reticulum OpenAPI Mustache Templates

These templates can be used with `openapi-generator-cli` to produce a working
Reticulum LXMF service and client from an OpenAPI specification. The generated
structure mirrors the `EmergencyManagement` example.

## Installation

Install the generator with the Python CLI or run it via Docker. Using the
Python package:

```bash
pip install openapi-generator-cli
```

Or with Docker:

```bash
docker run --rm -v "$PWD:/local" openapitools/openapi-generator-cli generate
```

## Usage

```bash
openapi-generator-cli generate \
    -g python \
    -i path/to/spec.yaml \
    -t templates \
    -o generated
```

The output will contain:

- `models.py` – dataclasses for all schemas
- `controllers.py` – controller classes with async handlers
- `service.py` – `LXMFService` subclass registering routes
- `server.py` – entrypoint starting the service
- `client.py` – simple client invoking the first operation
- `database.py` – example async database setup

Adjust the generated code as needed for your specification.

### Post-generation adjustments

- Set `auth_token` on the generated service and client if your deployment
  requires message authentication.
- Add additional schema dataclasses if your API defines objects outside the
  supplied OpenAPI spec.
