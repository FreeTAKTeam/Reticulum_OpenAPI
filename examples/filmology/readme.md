# Filmology Example

This example provides a minimal movie catalog built with **Reticulum OpenAPI**.
It demonstrates dataclass models, controllers, and an `LXMFService` that
enforces optional features like authentication tokens and JSON schema
validation.

The API contract resides in
[`API/FilmologyManagement-OAS.yaml`](API/FilmologyManagement-OAS.yaml).

## Components

| Folder | Description |
|-------|-------------|
| `Server/` | Service implementation with dataclasses, controllers and SQLite persistence. |
| `client/` | Simple `LXMFClient` usage that creates and retrieves a movie. |
| `API/` | OpenAPI specification. |

## Running the example

1. Install project dependencies from the repository root:

```bash
pip install -r requirements.txt
```

2. Start the server in one terminal:

```bash
python Server/server_filmology.py
```

   The service prints its identity hash on startup and expects the auth token
   `secret` for incoming requests.

3. In another terminal, run the client and supply the hash when prompted:

```bash
python client/client_filmology.py
```

The client sends a `CreateMovie` request followed by `RetrieveMovie`, showing
both persistence and server-side schema validation. The authentication token is
included in the request payload and must match the server's token.
