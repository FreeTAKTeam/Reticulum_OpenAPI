# Reticulum OpenAPI Mustache Templates

These templates can be used with `openapi-generator-cli` to produce a working
Reticulum LXMF service and client from an OpenAPI specification. The generated
structure mirrors the `EmergencyManagement` example.

## Usage

```bash
openapi-generator-cli generate \
    -g python \
    -i path/to/spec.yaml \
    -t path/to/templates \
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
