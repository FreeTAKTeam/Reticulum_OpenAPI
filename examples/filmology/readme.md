# Filmology Example

This directory contains the OpenAPI specification for **Filmology**, a sample
movie catalog service built for the Reticulum mesh network. The specification
demonstrates how to describe CRUD operations for a `Movie` resource before
generating a working service with Reticulum OpenAPI templates.

The API contract lives in [`API/FilmologyManagement-OAS.yaml`](API/FilmologyManagement-OAS.yaml).

## Running the example

1. Install project dependencies from the repository root:

```bash
pip install -r requirements.txt
```

2. Ensure you have `openapi-generator-cli` available. Install it via npm:

```bash
npm install @openapitools/openapi-generator-cli -g
```

3. Generate the service and client using the provided templates:

```bash
openapi-generator-cli generate \
    -g python \
    -i examples/filmology/API/FilmologyManagement-OAS.yaml \
    -t templates \
    -o examples/filmology/FilmologyService
```

4. Start the generated server:

```bash
cd examples/filmology/FilmologyService
python server.py
```

5. In another terminal, run the generated client:

```bash
python client.py
```

The client sends requests to the server over LXMF messages, showing how movie
records can be created and retrieved across the Reticulum network.

