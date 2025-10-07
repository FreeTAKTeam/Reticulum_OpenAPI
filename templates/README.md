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
- Extend the generated `server.py` with the same runtime CLI options used by
  the Emergency Management example (`--config-path`, `--storage-path`,
  `--display-name`, `--auth-token`, `--database-path`, `--database-url`, and
  `--link-keepalive-interval`). The scaffolded file only sleeps for 30 seconds;
  update it to wait on a signal-aware shutdown event so the service keeps
  running until interrupted, prints its identity hashes, and retries LXMF link
  establishment when necessary.
- Call `configure_database()` with a caller-supplied override before `init_db`
  to honour environment variables such as `EMERGENCY_DATABASE_URL` or CLI
  flags.
- Add additional schema dataclasses if your API defines objects outside the
  supplied OpenAPI spec.
- Mirror the gateway helpers if you need FastAPI adapters: load shared LXMF
  client configuration from `NORTH_API_CONFIG_PATH`/`NORTH_API_CONFIG_JSON`,
  expose `/notifications/stream`, and surface interface or link status in
  startup logs.
