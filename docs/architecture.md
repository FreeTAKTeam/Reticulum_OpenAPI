

# What it is

**Reticulum OpenAPI** is a framework to expose lightweight, REST-style APIs over the Reticulum mesh by using **LXMF messages** as the transport. 
the Payloads are **MessagePack-encoded** for compact transfer. 
# Core building blocks
``` mermaid
flowchart LR
  %% ===== Client Side =====
  subgraph C["Client Node"]
    AC["API Client\n(LXMF / Link)"]
    CC["MessagePack Codec"]
    RC["ResourceClient\n(file send)"]
    LC["LinkClient\n(RNS.Link)"]
  end

  %% ===== Network =====
  subgraph N["Reticulum Mesh Network"]
    LXM["LXMF (store-and-forward)"]
    RNS["RNS Router & Links"]
  end

  %% ===== Server Side =====
  subgraph S["Server Node"]
    AS["API Service\n(LXMF / Link)"]
    RS["Request Router\n(endpoint → handler)"]
    DS["Domain Services\n(e.g., EmergencyService)"]
    RCV["ResourceService\n(file receive)"]
    LS["LinkService\n(RNS.Link)"]
    CS["MessagePack Codec"]
  end

  %% Flow: LXMF request/response
  AC --> CC --> LXM --> AS
  AS --> CS --> RS --> DS --> RS --> CS --> LXM --> AC

  %% Flow: persistent link (interactive/streaming)
  AC -. open link .-> LC
  LC --> RNS --> LS --> AS
  LS -. stream/bidirectional .- LC

  %% Flow: large resources over link
  RC --> LC
  LC --> RNS --> RCV
```
* **Transports (two modes):**

  * **LXMF (store-and-forward):** asynchronous requests/replies packed in a single LXMF envelope—ideal for intermittent, low-bandwidth links. 
  * **RNS Link sessions:** interactive, lower-latency connections for streaming or bigger exchanges; the repo exposes **LinkClient**/**LinkService** primitives to keep links alive. ([GitHub][1], [reticulum.network][2])
* **Encoding:** all API payloads use **MessagePack**.
* **Resource transfer helpers:** **ResourceClient.send\_resource()** and **ResourceService.resource\_received\_callback()** support larger file moves over links. ([GitHub][1])
* **Scaffolding & docs:** architectural and protocol details live under `docs/Framework_design.md` and `docs/protocol_design.md`; service scaffolds sit in `templates/`. ([GitHub][1])

# How a request flows (LXMF mode)

1. Client encodes a request (MessagePack), addressed to the **server identity hash**.
2. LXMF delivers the envelope via Reticulum’s router.
3. The service decodes, dispatches to the handler, encodes the response, and replies by LXMF to the client identity.
   This is how the **EmergencyManagement** example works; the server prints its identity at start, and the client uses that hash to send requests. 

# When to choose each mode

* Use **LXMF** for command/response APIs and delay-tolerant operations.
* Use **Link sessions** for interactive exchanges and efficient large transfers.

## Class diagram

``` mermaid
classDiagram
direction LR

class LXMFApiClient {
  +sendRequest(endpoint, payload) : Response
  +sendAndWait(...)
  -codec : MsgPackCodec
  -lxmf : LXMFTransport
}

class LXMFApiService {
  +register(endpoint, handler)
  +onMessage(envelope)
  -codec : MsgPackCodec
  -router : RequestRouter
}

class LinkClient {
  +open(link_hash)
  +send(data)
  +close()
}

class LinkService {
  +on_link_established(link)
  +on_link_closed(link)
  +handle_stream(data)
}

class ResourceClient {
  +send_resource(path, to_identity) : Progress
}

class ResourceService {
  +resource_received_callback(meta, path)
}

class MsgPackCodec {
  +to_bytes(obj): bytes
  +from_bytes(b): any
}

class RequestRouter {
  +route(endpoint, payload) : Response
  -handlers: map
}

class LXMFTransport {
  +send(to_hash, content)
  +on_receive(cb)
}

class Identity {
  +hash
  +public_key
}

%% Example domain service used by the sample
class EmergencyService {
  +createEmergency(data) : Ack
  +getStatus(id) : Status
}

LXMFApiClient --> MsgPackCodec
LXMFApiClient --> LXMFTransport
LXMFApiService --> MsgPackCodec
LXMFApiService --> RequestRouter
RequestRouter --> EmergencyService
LinkClient ..> LXMFTransport
LinkService ..> LXMFTransport
ResourceClient ..> LinkClient
ResourceService ..> LinkService
LXMFApiClient --> Identity
LXMFApiService --> Identity

```
