# Examples

This directory contains sample applications built with Reticulum OpenAPI.

- `EmergencyManagement` – full-featured emergency management demo.
- `filmology` – OpenAPI specification for a movie catalog service.
- `LinkDemo` – minimal demonstration of establishing an RNS link, exchanging packets, and uploading a file.

## LinkDemo

1. Start the server:
   ```bash
   python examples/LinkDemo/server.py
   ```
   The service prints its identity hash.
2. Run the client in another terminal, replacing `<hash>` with the printed value:
   ```bash
   python examples/LinkDemo/client.py <hash> examples/LinkDemo/sample.txt
   ```
   The client establishes a link, receives an echo response, and uploads a file which the server stores in its working directory.
