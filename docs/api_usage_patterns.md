# API Usage Patterns

Examples of how to interact with the framework at different levels.

## Command Requests

Use the high level `LXMFClient` to send structured requests and await a
response:

```python
from reticulum_openapi.client import LXMFClient

client = LXMFClient()
payload = {"echo": "hello"}
reply = await client.send_command(server_hash, "Echo", payload, await_response=True)
print(reply)
```

## Raw Packets

When a real‑time link exists you can send arbitrary bytes using an
`RNS.Packet`:

```python
import RNS

dest = RNS.Destination(server_identity, RNS.Destination.OUT, RNS.Destination.SINGLE, "openapi", "link")
link = RNS.Link(dest)
RNS.Packet(link, b"status?").send()
```

## Resource Transfers

Large binary data can be moved over the link with `RNS.Resource`:

```python
import RNS

link = RNS.Link(dest)
data = open("report.bin", "rb").read()
RNS.Resource(data, link, callback=lambda r: print("transfer complete"))
```

