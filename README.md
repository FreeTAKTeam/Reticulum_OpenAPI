# Reticulum OpenAPI
he Reticulum LXMF-based API system aims to offer a secure, portable, and efficient API layer on top of a resilient mesh network

# Reticulum LXMF-based OpenAPI System Requirements

## Protocol Design

The system will use the Reticulum Network Stack and its **LXMF (Lightweight Extensible Message Format)** protocol to implement API calls over a secure, delay-tolerant mesh network. All API interactions are encoded as LXMF messages, leveraging Reticulum’s end-to-end encryption and self-routing capabilities. The design supports **two interaction models**:

* **REST-style Model:** Emulates traditional HTTP REST semantics. Each request message includes an operation type (e.g. GET, POST, PUT), a target resource path (and any query parameters), and possibly a JSON payload (for POST/PUT). The response message includes a status code (mirroring HTTP response codes) and a JSON result or error payload. This model preserves familiar RESTful patterns (resources and verbs) within the LXMF message context.

* **Command-oriented Model:** Provides a compact, message-driven alternative optimized for low bandwidth. Each request specifies a *command* (a short identifier or the OpenAPI operationId) and any necessary arguments, without explicit HTTP verbs or long URLs. The server interprets the command and parameters to perform the appropriate action. Responses in this model use a simplified status indicator or code (which can still align with standard HTTP codes) and any result data. This model reduces overhead by eliminating verbose HTTP-like syntax, suitable for constrained links.

In both models, **each complete API call consists of exactly two LXMF messages**: one request and one response. **Every LXMF message represents a single API interaction** from client to server or vice-versa, avoiding any multi-packet sequencing at the application layer. There are *no multi-part or fragmented messages* for a single request/response; the entire request (including parameters and body) must fit in one LXMF message, and likewise for the response. This simplifies processing and ensures reliability, as Reticulum’s transport will handle any necessary low-level fragmentation and reassembly within its 500+ byte MTU constraints. The LXMF protocol is explicitly designed for minimal bandwidth usage and efficient routing, making single-message exchanges feasible even on very low data rates.

**Client-Server Message Flow:** A client uses the server’s Reticulum **destination address** (a 16-byte cryptographic hash of the server’s identity key) as the LXMF message destination, and includes its own address as the source. The Reticulum network automatically routes the message through any available paths (radio, TCP tunnel, etc.), even across multiple hops, with no special configuration needed. If the server is not immediately reachable (e.g. offline or out of range), optional **LXMF Propagation Nodes** will store-and-forward the encrypted message until it can be delivered. This enables a *delay-tolerant networking* approach – requests and responses may be delivered with high latency, but remain reliable. Each request message should include a **correlation identifier** (e.g. a request ID) so that the client can match the asynchronous response to the originating request when it arrives. The server simply echoes this ID in the response. Reticulum’s design provides *unforgeable delivery acknowledgments* at the packet level, so no additional ACK messages are needed in the application protocol.

**Stateless Interaction:** The API interactions are essentially stateless. The server does not maintain persistent sessions; each LXMF request contains all information needed to process that call (operation, parameters, etc.), similar to a stateless REST API. The server can handle multiple clients and calls concurrently (limited only by computing resources and network throughput). Reticulum’s lightweight request/response mechanism and sequencing support ensure messages can be processed reliably in order if needed. The design assumes *idempotent processing* for GET requests and encourages clients to handle potential duplicate deliveries or retries gracefully, as is common in distributed message systems.

This approach allows *any OpenAPI-defined service* to be offered over Reticulum/LXMF with minimal changes: clients issue LXMF-encapsulated requests instead of HTTP calls, achieving a “portable” API that functions over RF links, local mesh, or internet-tunneled Reticulum networks alike. The protocol design takes advantage of Reticulum’s cryptographic routing and encryption to provide a secure API without the overhead of TCP/IP or HTTP, meeting the goal of **operating in extremely low-bandwidth and high-latency environments**.

## Message Format

All API messages use a **JSON-based payload** to represent the request or response data, which is then *compressed and encoded* for transport via LXMF. JSON provides a universal, human-readable structure for parameters and data, while compression (e.g. using DEFLATE or a similar algorithm) significantly reduces message size to suit bandwidth constraints. The compressed JSON is placed into the LXMF message payload (the *Content* field) as a binary blob, or encoded (e.g. base64) if necessary for safe transmission. LXMF messages themselves are structured as a timestamp plus content, title, and fields sections; this design allows flexibility. In this system, we propose using the **Content** section for the main JSON payload, and the optional **Fields** dictionary for any additional metadata that aids in routing or interpretation (if needed). Each message’s *Title* field may be left empty or used for a brief human-readable description (not strictly required for operation).

**Request Message Structure:** In REST-style mode, the JSON payload includes keys for the HTTP-like components: for example:

```json
{
  "req_id": "12345",
  "method": "GET",
  "path": "/resource/123",
  "query": { "filter": "all" },
  "body": null
}
```

* `req_id`: a unique identifier for this request (string or number) to correlate with the response.
* `method`: the operation type, e.g. "GET", "POST", "PUT".
* `path`: the endpoint path (as defined in the OpenAPI spec) the client wants to access. Path parameters can be included in this string (e.g. `/resource/123` with `123` as an ID parameter).
* `query`: an object of query parameters (if any) where keys are parameter names and values are the provided values. For a GET request, all inputs are typically in the query or path.
* `body`: the request payload for methods like POST/PUT, encoded as a JSON object (or `null` if no body). This corresponds to the OpenAPI request schema.

For the command-oriented mode, the request JSON might be simpler, for example:

```json
{
  "req_id": "12346",
  "command": "ActivateDevice",
  "args": { "device_id": 123, "mode": "safe" }
}
```

* `command`: a short name or code for the operation (often derived from the OpenAPI operationId). This replaces the method/path in identifying the action.
* `args`: an object holding any parameters or body data the command requires (could also be an array or primitive if a single argument is needed). In this example, it provides a device ID and a mode setting.

Both styles include the `req_id` for correlation. The JSON keys are kept short and the overall structure minimal to reduce size. After constructing the JSON, it is compressed (e.g. with gzip or zlib) and then encoded into the LXMF message. **Each LXMF message represents one request, so the entire JSON must fit into a single message’s payload.** The Reticulum stack can handle multi-packet transport transparently if the payload is larger than a single frame, but the application layer does not split one logical request across multiple messages.

**Response Message Structure:** The server replies with a corresponding LXMF message whose JSON payload contains the outcome. In REST-style mode, the response JSON includes:

```json
{
  "req_id": "12345",
  "status": 200,
  "body": { ... },
  "error": null
}
```

* `req_id`: mirrors the request ID so the client knows which request this is answering.
* `status`: a numeric status code analogous to HTTP status codes (200 for success, 404 for not found, 400 for bad request, 500 for server error, etc.). The server chooses the code based on the operation’s result as defined in the OpenAPI spec.
* `body`: the response data (if any) as a JSON object or value. For example, on a successful GET it might contain the resource data. If the request did not produce data (e.g. a successful POST that created something), this could be `null` or an acknowledgment message.
* `error`: an error description if applicable. On success, this is null or omitted. On failure, this may contain a brief message or error code explaining the error (in addition to an error status code).

In the command-oriented model, the response might use a slightly different convention but similar idea:

```json
{
  "req_id": "12346",
  "status": 0,
  "result": { ... },
  "error": null
}
```

For example, `status: 0` could mean success (whereas non-zero or negative might indicate various errors), or the system may still use HTTP-like codes even in command mode for consistency. The `result` field carries any returned data from the command. The `error` field (or an error code) provides info if the command failed.

Like requests, response JSON is compressed and inserted into a single LXMF message. The LXMF **Destination** of the response will be the original requester’s address (as provided in the request’s Source field), and the **Source** will be the server’s address, allowing the client to verify it came from the correct server. We avoid any multi-part responses; if a requested operation would yield a very large dataset, the API should either restrict the size or require the client to request data in smaller chunks (e.g. via pagination or separate calls) to adhere to the one-message-per-interaction rule.

**Encoding and Size Optimizations:** All JSON payloads should omit unnecessary whitespace and long key names. Use concise keys (as seen in the examples) and rely on schema knowledge to keep messages small. The compression step will further reduce repetitive text (for instance, the overhead of JSON keys like `"status"` becomes negligible after compression if repeated). Given Reticulum can operate on links as slow as \~500 bits/s, every byte saved matters. However, since Reticulum can automatically compress and segment large transfers, the system can carry moderately sized JSON payloads when needed (e.g. a few kilobytes for a complex object or an OpenAPI schema), with the trade-off of longer transmission time. The design goal is to **keep typical request/response payloads to only a few hundred bytes compressed**, to ensure timely delivery on low-bandwidth channels.

No additional encryption or wrapping is applied to the JSON payload. It is transmitted as an opaque compressed blob within the LXMF Content. The integrity and confidentiality of the message are inherently provided by Reticulum (see **Security** below). The LXMF **Fields** dictionary could optionally be used to carry a few meta-fields (like `method` or `command` and `status` codes) outside of the compressed blob, which might allow a recipient to quickly inspect the message type without decompression. However, for simplicity and minimal code paths, the design treats the compressed JSON as the primary content containing all necessary info. The entire message is self-contained: the client or server only needs to decompress and parse the JSON to fully understand the request or response.

## Security

Security is fundamentally provided by the Reticulum network layer and its cryptographic identity scheme. Each server or client node has a **Reticulum Identity**, which consists of a pair of cryptographic keys (Curve25519) used for encryption and signing. From these keys, Reticulum derives a 16-byte **destination hash** that serves as the node’s address on the network. These identities are the basis for authentication and trust:

* **Endpoint Authentication via Identity:** Every LXMF message includes the *Source* and *Destination* fields which are the hashes of the sender and receiver identities, respectively. Additionally, each message carries an Ed25519 **digital signature** made by the sender’s private key, covering the message contents and addressing. The receiving node (client or server) uses the sender’s public key to verify this signature. This means the API server can cryptographically verify which client sent a given request (and vice versa for responses). Impersonation is virtually impossible because only the legitimate identity holder can produce a valid signature for their hash address. Thus, RNS identities act as an implicit authentication mechanism – similar to API keys or tokens in HTTP, but baked into the network protocol.

* **Access Control:** By default, any node knowing the server’s address could send requests, but the server can enforce an access policy by checking the Source identity of incoming messages. For example, the server might maintain a whitelist of authorized client identities or require that certain commands only be executed by privileged identities. This would be an application-level rule, since Reticulum itself does not restrict who can send to an address. The assumption in the minimal design is that either the API is open to all (public) or that trust is managed via exchanging identity information out-of-band (similar to sharing an API key). Because identities are long-lived (unless rotated) and tied to cryptographic keys, they can serve as stable client identifiers for audit or permission purposes.

* **End-to-End Encryption:** Reticulum provides encryption for all traffic by default. When a client sends a request to the server’s destination, the payload is encrypted such that only the server can decrypt it. Reticulum achieves this using an ECDH key exchange (X25519) to derive a symmetric encryption key for the session, employing AES-256 in CBC mode with HMAC-SHA256 for authenticity. This process gives **forward secrecy** (each session uses ephemeral keys) and strong encryption without the application needing to do anything extra. Therefore, the JSON content of our API messages is already confidential on the wire – only the intended recipient’s Reticulum node can decrypt it. Intermediate nodes (relays or propagation servers) cannot read or alter the content. The Ed25519 signature on each message further ensures integrity; if a message were tampered with in transit, the signature check at the receiver would fail and the message would be rejected.

* **No Additional Payload Encryption:** In line with the requirement to avoid redundant layers, the system does *not* add any custom encryption or signature on the JSON payload itself. We rely entirely on Reticulum’s built-in security for both confidentiality and authenticity. This avoids overhead and complexity. For example, we do not use JSON Web Tokens, HTTPS/TLS, or message-level PGP encryption – all those would be superfluous since Reticulum already guarantees encryption by default (using Curved25519 keys and Fernet-like token encryption) and authenticity through identity signatures. This keeps the payload format simple (plain JSON) and small.

* **Identity Exchange and Trust Bootstrap:** It is assumed that clients know the server’s identity (address and public key) in order to send requests. This can be achieved via Reticulum’s **announce** mechanism or through an out-of-band sharing (for instance, scanning a QR code containing the server identity, which is a common practice in LXMF apps). When the server identity is known, Reticulum can automatically route to it and perform any needed key exchanges. Similarly, the server can obtain the client’s public key either from the first contact (Reticulum may include the public key in the link handshake) or by the client’s prior announcement on the network. In any case, once a message is received, the receiving node has what it needs to verify the signature and thus the sender’s identity.

* **Privacy and Anonymity:** Reticulum allows *initiator anonymity*, meaning a node can communicate without revealing its full identity if configured so. However, for an authenticated API scenario, we generally assume clients will use their real identity (so the server knows who is calling). An anonymous mode could be possible for open public APIs where you don’t need to know the caller (similar to not requiring API keys), but even then the message is encrypted and signed by some ephemeral identity. The system’s minimal subset of OpenAPI likely doesn’t cover OAuth or API key security schemes – instead, RNS identity serves that role. If needed, an identity could be treated as analogous to an API key issued to a client. The cryptographic strength of the identities (Curve25519 keys, 256-bit security) is more than sufficient to ensure that only authorized parties can access protected endpoints.

In summary, **the security model leverages Reticulum’s cryptography for both authentication and encryption**. Each API message is secure in transit and can be attributed to a specific client or server. The server and clients should handle key management (ensuring their private keys remain safe, rotating keys if necessary for security policy, etc.), but the protocol itself does not require any passwords, tokens, or higher-level encryption of payloads. This keeps the system lightweight and aligned with Reticulum’s philosophy of security-by-default without handshakes or heavy negotiation. The result is a **secure, trustable API channel** where both parties can be confident in the identity of the other and in the privacy of their communication.

## Client/Server Responsibilities

Both the server and client components have specific responsibilities to implement this LXMF-based API system. This section outlines those roles.

### Server Responsibilities

* **Identity and Addressing:** The server must have a Reticulum cryptographic identity (public/private keypair). It should either generate one or use a pre-configured identity, and make its *destination hash* (address) known to prospective clients (for example, via documentation, QR code, or a Reticulum announce). The server runs an LXMF-enabled node (e.g., using the `lxmf` library or an LXMF router daemon) listening for incoming messages addressed to its identity.

* **OpenAPI Definition (Minimal) Loading:** The server should maintain a machine-readable API definition (conforming to the supported OpenAPI subset) that describes all its endpoints, expected parameters, and responses. This could be hard-coded or loaded from an OpenAPI JSON/YAML file. The definition is used both for documentation (to send to clients on discovery requests) and for request validation/routing.

* **Message Handling Loop:** The server continuously listens for LXMF messages (requests). When a message arrives, the server:

  1. Decrypts and verifies it (Reticulum does this automatically before delivering it to the application).
  2. Parses the JSON payload (after decompression) to retrieve the `req_id`, requested operation (method/path or command), and parameters.
  3. Validates the request against the API schema: e.g., ensure required parameters are present and of correct type, and that the path or command corresponds to a known endpoint. If validation fails or the endpoint is not found, the server prepares an error response (e.g., status 400 Bad Request or 404 Not Found).
  4. Authenticates the source if required. For protected endpoints, check the sender’s identity against allowed identities. If not authorized, respond with an error (e.g., 401 Unauthorized or 403 Forbidden). (In the minimal design, this may be optional or simply not implemented, but it’s an important consideration if the API isn’t public.)

* **Executing the Operation:** If the request is valid and authorized, the server invokes the corresponding handler or business logic. This could be an internal function call, a database query, hardware interaction, etc., depending on the API’s purpose. Because the system is meant to be **portable and Python-based**, one can imagine the server being a Python program where each API endpoint is implemented as a function. The server maps the incoming operation (by method/path or command name) to the correct function.

* **Preparing the Response:** After executing the operation, the server constructs a response message. It will:

  * Determine the appropriate **status code**. For example, if the operation succeeded, 200 (OK) or 201 (Created) might be used; if there was an application error or exception, perhaps 500; if the input was invalid, 400, etc. The set of codes should align with what the OpenAPI spec for that operation declares.
  * Populate the **response body** data. For a query operation (GET), this might be the requested resource or data structure in JSON form. For a command, it could be a result value or acknowledgment. The server must ensure this data conforms to the response schema defined in the OpenAPI spec (e.g., correct fields and types).
  * If an error occurred (either in processing or due to bad input), include an error message or code in the response (and possibly an `error` field explaining the failure).
  * Include the original `req_id` so the client can match the response.
  * Structure this information into the JSON response format as described in **Message Format**. Then compress it and set it as the LXMF Content.

* **Sending the Response:** Using the Source address from the request (which becomes the destination for the reply), the server sends out the LXMF response message. The Reticulum stack will encrypt and route it to the client. The server should use the same LXMF *Title* and *Fields* conventions if any were chosen (though typically not needed beyond content). The Ed25519 signature will be attached automatically by the LXMF layer using the server’s identity key, so the client can verify it came from the correct server.

* **Schema Discovery Support:** The server must support the discovery mechanism (detailed in the next section). Essentially, it should recognize requests for the API schema (e.g., a GET to a known path like `/openapi.json` or a special command) and return the current OpenAPI specification (filtered to the minimal subset). This means the server either keeps the spec in memory or can generate it on the fly from its internal representation of endpoints.

* **Resource Constraints:** Since this system should run on modest hardware (even embedded devices running Python), the server is responsible for optimizing its use of resources. It should compress/uncompress data efficiently (possibly using standard libraries). It should avoid very large responses or heavy computations in a single request that would strain low-power devices. If needed, the server can enforce limits (e.g., refuse requests that would yield huge data beyond one message, or send an error indicating the request is too large). The server should also handle Reticulum network configuration (ensuring it’s connected to the relevant interfaces like LoRa, etc., but that is outside the API logic per se).

* **Parallel Operation:** In some use cases, the server might handle multiple LXMF requests concurrently (if the underlying platform and LXMF library allow it, via threading or async IO). The minimal design can be single-threaded (processing one at a time) to keep it simple, but it should not deadlock the Reticulum service. If using the `lxmf` Python library, messages may arrive via callback or queue that the server processes. The server should ensure that processing an API call does not block the handling of new incoming messages indefinitely (for instance, by offloading any long processing to a background thread or by quick acknowledgement).

* **Logging and Monitoring:** It is advisable (though not strictly required) that the server log requests and responses (at least in summary) for debugging and auditing, especially since network conditions are unpredictable. Monitoring can help ensure the system is functioning and help diagnose issues like no responses or malformed messages.

### Client Responsibilities

* **Client Identity:** Each client also needs a Reticulum identity (keypair and address). This identity is used as the Source for requests, allowing the server to authenticate the client. A client might generate its own identity on first use (many Reticulum apps do this automatically) and should persist it for reuse so that it remains recognizable to servers across sessions.

* **Server Identity Knowledge:** Before making requests, the client must know how to address the server. This means obtaining the server’s Reticulum destination hash (and ideally verifying it belongs to the right service, e.g., via a fingerprint or trust mechanism). The client could be pre-configured with this (for a known API service), or could discover it if the server broadcasts announcements. In a minimal scenario, we assume the client is provided with the server’s address (e.g., a user enters it or scans it).

* **API Schema Retrieval:** Unless the client is hard-coded to call specific endpoints, it should retrieve the API schema from the server using the discovery mechanism. The client sends an LXMF request to the designated discovery endpoint/command (e.g., GET `/openapi.json`). When the response arrives with the OpenAPI spec, the client parses this (JSON parsing for the spec which is likely JSON). This step allows the client to **understand available endpoints, required parameters, and data structures** without any external documentation, fulfilling the OpenAPI goal of self-describing services. In constrained devices, the client might not want to store the entire spec in memory indefinitely; it could parse just what it needs or cache it on disk.

* **Request Construction:** To call an API operation, the client will:

  1. Determine the operation details. This can be done either manually (if the client is coded against a known API) or dynamically by referring to the discovered spec. For example, the client finds the path and method for the feature it wants to use, along with what parameters are required.
  2. Create a JSON object for the request as per the Message Format. This includes generating a new `req_id` (could be a simple incrementing number or a UUID string) to tag the request.
  3. Fill in the method and path (for REST mode) or the command name (for command mode), and supply all needed parameters. For a GET, this might mean populating the `query` object; for a POST, putting the payload in `body`; for command mode, putting arguments in `args`.
  4. Validate its own input against the schema if possible. A smart client might use the OpenAPI parameter schemas to immediately catch errors (e.g., missing required fields, or wrong data type) before sending, to avoid a round-trip for a 400 Bad Request. This is especially important in high-latency networks to save time and bandwidth. For example, if the spec says a field must be an integer, the client can ensure it’s not sending a string in that field.
  5. Compress the JSON and send it via an LXMF message to the server’s address. The client’s Reticulum layer will handle encryption and send it out over the available interface (which could be a radio link, etc.).

* **Waiting for Response:** After sending a request, the client must wait for the response. Because responses might be delayed (especially if the server was offline and a propagation node is holding the message, or simply due to slow link speed), the client should be prepared for asynchronous reception. Typically, the LXMF library on the client can notify when a message arrives (or the client can poll a mailbox). The client might implement a timeout if a response isn’t received within a certain window, and possibly retry the request if idempotent. The appropriate timeout could be on the order of seconds to minutes depending on network expectations. (For instance, on a direct LoRa link, a few seconds might suffice; via long-range multi-hop, one might wait a minute or more.)

* **Response Handling:** When a response message arrives:

  1. The client verifies the message’s Source is the expected server identity. This is normally automatic: if the message is properly signed and came through the Reticulum stack addressed from the server, we trust it. If for some reason an unexpected Source appears, the client should discard it or treat it as a potential spoof (though spoofing is infeasible if signatures are correct).
  2. Decompress and parse the JSON payload.
  3. Match the `req_id` with an outstanding request. The client likely keeps track of requests it has sent that are awaiting responses. By finding the matching ID, it knows which operation this response corresponds to.
  4. Check the `status` code. If it’s a success code (e.g. 200), proceed to process the data in `body` (or `result`). If it’s an error code (e.g. 404 or 500), decide how to handle it. The client might display an error to the user or take corrective action (for example, if 401 Unauthorized, maybe prompt for credentials, though in our design credentials = identity, so that case might mean the client’s identity isn’t authorized).
  5. Use the response data. For example, if the response was to a GET list query, the client might update its UI with the list of items returned. If it was a command to change a setting, the client might log success or update local state accordingly.

* **Efficiency Considerations:** The client should minimize how often it requests the full API spec. It can cache the spec (using the `info.version` field from the OpenAPI document to detect changes). Only if the client suspects the API has changed (or on first connection) should it fetch the schema. Also, the client should batch requests only if necessary. Since each request is expensive over low bandwidth, a client might try to avoid overly chatty behavior. For example, rather than fetching one item at a time in a loop, a well-designed API could offer a batch query, and the client would use that to reduce message count.

* **Compatibility and Platform:** The client can run on any Python-capable platform (PC, Raspberry Pi, Android Termux, etc.). It should use the same `rns`/`lxmf` libraries. Embedded scenarios (like a microcomputer in an IoT device) can run the client logic to interact with the server API for configuration or data retrieval. The client application is responsible for integrating this communication into whatever user interface or automation is needed on that device.

* **Error Handling and Retries:** In a mesh network, messages might occasionally fail to deliver due to node movement or interference. The client should handle no-response scenarios gracefully. This could mean retrying the request after a timeout, or alerting the user to a connectivity issue. Because Reticulum assures delivery if a path exists (with acknowledgements at the packet level), repeated failures likely indicate the server is unreachable. The client might then pause and retry later rather than continuously sending.

In essence, the client’s role is analogous to an HTTP API client but adapted to an *offline-capable*, asynchronous environment. It discovers the service, formulates requests according to the service’s schema, and interprets responses, all while handling the intricacies of a highly variable network link. By dividing responsibilities as above, we ensure a clear separation: the server focuses on implementing and exposing functionality, and the client on consuming that functionality, with the Reticulum/LXMF layer transparently handling secure delivery.

## Discovery Mechanism

To make the API self-describing and eliminate the need for prior hardcoded knowledge, the system includes an **API schema discovery mechanism over LXMF**. This allows clients to retrieve the OpenAPI specification (or an equivalent endpoint list) from the server itself. The discovery is designed to be simple and low-overhead:

* **Discovery Endpoint:** The server shall expose a special endpoint that returns the API definition. In the REST-style model, a conventional choice is an HTTP-like path such as `/openapi.json` or `/api/schema`. A client would send a GET request for this path (e.g., `method: "GET", path: "/openapi.json"` in the request JSON). The server responds with a 200 status and the body containing the OpenAPI document (in JSON form). In the command model, an analogous approach could be a reserved command like `"GetSchema"` with no additional args, which triggers the same behavior. The system can support either or both, but implementing it as a normal path in the OpenAPI spec itself is straightforward.

* **Schema Format:** The returned schema is a JSON representation of the **minimal OpenAPI 3.x spec** for the API. It will include the key sections needed to describe available endpoints: the list of paths and operations, the components schemas for data models, and basic metadata. By using the OpenAPI format, we ensure it’s a standard, machine-readable blueprint. Tools or libraries on the client side could even directly feed this into OpenAPI parsing utilities if available in Python, although that might be heavy for embedded use. At minimum, the client can traverse this JSON to find what it needs.

* **Minimal Subset and Size:** The server should trim any unnecessary parts of the OpenAPI document to keep it small. For example, descriptive text, examples, and external documentation references in the spec are not strictly needed for the client to call the API and can be omitted to save space (or included only if they are brief and deemed useful for human operators). The focus is on **endpoints, parameters, and schemas**, which are essential. The server may pre-generate a minimized version of the OpenAPI JSON for this purpose. If the full original OpenAPI is already minimal, it can use that directly. Since OpenAPI 3.0+ is verbose, compression will be applied to this response as with any other, but it’s wise to avoid extremely large specs. In practice, APIs designed for mesh networks will not have hundreds of endpoints, so the spec might be only a few kilobytes at most when compressed.

* **Delivery as LXMF:** Because the OpenAPI JSON might be larger than typical data responses, it may span multiple Reticulum packets, but it will still be delivered as a single LXMF message (Reticulum’s reliable transport can handle larger payloads by automatic segmentation). The server will set the response’s `Content` to the compressed OpenAPI JSON and likely use a 200 status. The client, upon receiving it, will decompress and parse it.

* **Example Structure:** A truncated example of what the discovery response contains:

  ```json
  {
    "openapi": "3.0.3",
    "info": { "title": "My API", "version": "1.0.0" },
    "paths": {
      "/resource/{id}": {
        "get": {
          "summary": "Retrieve resource",
          "parameters": [
            { "name": "id", "in": "path", "schema": { "type": "integer" }, "required": true }
          ],
          "responses": {
            "200": {
              "description": "OK",
              "content": { "application/json": { "schema": { "$ref": "#/components/schemas/Resource" } } }
            },
            "404": { "description": "Not Found" }
          }
        },
        "put": { ... }
      }
    },
    "components": {
      "schemas": {
        "Resource": {
          "type": "object",
          "properties": {
            "id": { "type": "integer" },
            "name": { "type": "string" },
            "status": { "type": "string", "enum": ["active","inactive"] }
          },
          "required": ["id","name"]
        }
      }
    }
  }
  ```

  This illustrates the minimal subset: basic info, one path with operations, parameters (path param `id`), response codes (200 and 404) with a JSON schema for the response body (referencing a component schema), and the schema definition for the Resource object. This corresponds to what OpenAPI normally includes for each endpoint, but without verbose documentation. The actual wire format would be compressed JSON.

* **Client Interpretation:** Once the client has this schema, it can programmatically determine how to formulate requests. For instance, it sees that `GET /resource/{id}` requires an integer `id` path param and will return a `Resource` object. If the client has a high-level interface (like a code-generated stub), it could use this info to provide a function call like `get_resource(id)`. In a simpler client, it might just use the spec to validate inputs and know which endpoints exist. The spec also tells the client what status codes to expect. If an operation documents a 404 response, the client knows to handle “not found” as a possible outcome.

* **Dynamic vs Static Discovery:** In some deployments, clients might be pre-loaded with the API spec (especially if they are built for a specific API). In those cases, the discovery step can be skipped unless verifying that the server’s version matches. However, including a discovery mechanism is crucial for generality, enabling truly **portable APIs** – any client that understands this system can approach any server, fetch its spec, and then interact with it, all through the Reticulum network without needing internet or prior arrangements.

* **Security of Discovery:** The spec itself is not sensitive (it’s like a public interface description), but it is still delivered encrypted over Reticulum. If a server wanted to restrict who can download the spec (perhaps to hide its capabilities from unknown nodes), it could require the discovery request to be signed by a known identity or only respond if it recognizes the Source. In the minimal design, we assume the API spec can be shared with any requester, as it’s akin to public documentation. Still, it’s at the server’s discretion – this could be noted as an assumption that the API is not secret, only the data exchanged is protected.

* **Constraints:** We avoid multi-step discovery (such as paginating the spec or requiring multiple queries). The entire API definition should be delivered in **one message** if possible. If the spec is extremely large (which is unlikely in the target use-cases), and cannot fit, the system might either compress further or, if absolutely necessary, break it into parts. But since one of the core requirements is to *“avoid multipart or sequenced messages”*, even the discovery should strive to fit in a single message. This might mean the spec provided is not a full-blown OpenAPI with every detail, but a trimmed version containing just enough for clients to know how to call the API.

* **OpenAPI Version Compatibility:** The discovery should indicate the OpenAPI version it’s using (the example above uses `"openapi": "3.0.3"`). The client can parse this. The system is meant to support OpenAPI 3.0 and above (including 3.1) in the subset form, so the server could choose to supply a 3.0.3 document or a 3.1.0 document. In practice, the differences don’t matter much for our usage (3.1 mainly changes JSON Schema usage). A client should not break if it sees 3.1.0, as long as it sticks to the features we outline. Including the version helps with forward compatibility.

In summary, the discovery mechanism uses a **standard OpenAPI description delivered on-demand via LXMF**. This fulfills the OpenAPI’s purpose of letting clients *“discover and understand the capabilities of the service without access to source code or documentation”*. It ensures that our Reticulum-based API is self-contained and usable in the field, even if no internet or external documentation is available – a critical feature for offline and mesh networks.

## Supported OpenAPI Features

The system is designed to implement a **minimal subset of OpenAPI 3.x** that is sufficient to describe and enforce the API contract in a resource-constrained, message-oriented environment. We outline here which OpenAPI features are supported and which are omitted or simplified.

**Supported Features (Minimal Subset):**

* **Paths and Operations:** The core of the OpenAPI document – the **paths** object – is supported. Each path (endpoint) and its allowed HTTP **methods** (operations) are included. We specifically support common methods needed for basic REST semantics: **GET, POST, PUT** (as mentioned in requirements) and likely **DELETE** as well, since it’s another primary operation in CRUD APIs (DELETE wasn’t explicitly listed in the prompt, but it is analogous in complexity to the others and easy to include). These operations are defined just as in OpenAPI: under each path, methods have their details. In command-oriented usage, the existence of an operation in the OpenAPI spec implies a corresponding command (often we will use the operation’s `operationId` as the command name).

* **Parameters:** We support **path parameters** and **query parameters** for operations, with their schema definitions. Path parameters are identified by curly braces in the path (e.g., `/resource/{id}`) and must be marked required. Query parameters are listed as `in: query` in the OpenAPI spec. They can be primitive types (string, number, boolean) or even arrays/objects if needed, but to keep things simple, we assume primarily primitive types or small arrays of primitives. Each parameter can have a schema specifying type, and possibly constraints like max length, etc. The client and server will utilize these parameter schemas: the server to validate incoming requests, and the client to format queries properly. **Header and cookie parameters** are not supported in this minimal system – since we are not actually using HTTP, there is no use for HTTP headers or cookies. Any metadata that would traditionally go in a header (like an API key) is handled by the network identity instead. Thus, in the OpenAPI spec, parameters of `in: header` or `in: cookie` should be absent or ignored. Only path and query parameters matter for our use case.

* **Request Body:** The system supports operations that have a request body (typically for POST or PUT). In OpenAPI, a request body is defined with a JSON schema (under `requestBody -> content -> application/json -> schema`). We include those definitions. The content media type is effectively fixed as `application/json` for all requests and responses in this system. Other media types (like form data, XML, images, etc.) are not supported in the minimal subset. If binary data needs to be sent, it should be base64-encoded and put inside the JSON body (and the schema can specify a format like binary or base64 string). The server will accept and the client can send JSON bodies according to the specified schema. For example, a POST to create a resource might expect a JSON object with certain fields as defined by a schema in components. The server will validate that the body matches the schema (to the extent feasible) and then process it.

* **Responses:** Each operation can define expected responses with **status codes** and JSON schemas for the response body. We support multiple response definitions per operation (e.g., a 200 for success and a 404 for not found, etc.), though in practice the server will choose one code when sending a response. The OpenAPI spec typically includes a default or specific error codes, which we will include for completeness. The **HTTP status codes** are used exactly as in a normal API. We don’t invent new codes; 200-series for success, 400-series for client errors, 500-series for server errors, etc., as per RFC7231 and the IANA registry. The minimal subset means we won’t use extremely esoteric codes – mainly common ones such as 200, 201, 204, 400, 401, 403, 404, 500 (and maybe a few others like 422 Unprocessable if doing validation). Clients and servers should handle at least these appropriately. Each response may have a JSON schema describing the content. We support that by including the schema in the OpenAPI spec (often via `$ref` to a component schema for reuse) and the server will ensure its output matches it. If a response has no body (like 204 No Content), the spec can indicate that (or we simply send an empty body). The important part is that clients can read the spec and know, for instance, that a 404 response has no content or that a 200 response returns, say, a `Resource` object.

* **Schemas (Data Models):** The system supports JSON Schema definitions for request and response bodies and for parameter types. In OpenAPI 3.0, the schema is a subset of draft-04/ draft-07 JSON Schema. Our minimal subset will cover standard JSON types: `integer`, `number`, `string`, `boolean`, `object`, `array`. Within object schemas, we support defining properties and using `required` to mandate certain fields. We also allow fixed enums for strings (as shown in the example with `"status": {"enum": ["available","pending","sold"]}`) because that’s straightforward to implement. Constraints like maximum, minimum, length limits, regex patterns, etc., can be part of the schema, but the server may or may not enforce all of them strictly in the first iteration (it might focus on type and presence, leaving deeper validation as a later improvement). However, including them in the spec is useful for documentation and potential client-side validation. Complex JSON Schema features like oneOf/anyOf, polymorphism (discriminator), or advanced array serialization are **not** in the minimal subset to avoid adding complexity. Every schema should ideally be statically defined (no open-ended polymorphism), and if there are variants, they could be represented as separate endpoints or a simple field indicator in the data rather than a oneOf in the schema.

* **OpenAPI Metadata:** Basic metadata in the OpenAPI document such as the `info` section (title, version) is supported. The **version** is important to allow clients to detect changes. If the server updates its API, it should increment the version; clients might fetch the new spec and see a version bump to know they should refresh their understanding. We support including the `info.description` in a minimal way if needed (short description of the API), but lengthy documentation is discouraged in the delivered spec due to size. The `servers` section in OpenAPI (which normally lists base URLs) is not particularly relevant in Reticulum context – there is effectively one “server” which is the Reticulum address. We might either omit `servers` or include a placeholder (like `"servers": [{"url": "lxmf://<hash>"}]` just for completeness, though `lxmf://` is a notional scheme). This is optional, and clients anyway know the server via other means.

* **Reusable Components:** We do allow defining **components/schemas** in the OpenAPI doc to avoid repetition. Since the OpenAPI subset is processed by our own code (not a full OpenAPI validator), it’s not strictly necessary to use `$ref`, but for clarity and conciseness of the spec, it’s beneficial. For example, the spec can define a schema for a `Resource` object in the components and then reference it in multiple endpoints. The client should be able to resolve those `$ref` internally (which is straightforward by looking up the component). We thus support `$ref` references to `#/components/schemas/...`. We probably do not need other component types like `parameters` or `responses` since the API likely isn’t huge; but we can allow them conceptually. We **do not** use OpenAPI’s `examples`, `deprecated` flags, or other verbose metadata in this minimal profile.

* **Operation Identifiers:** We recommend each operation in the OpenAPI spec has an `operationId` (a unique string) for two reasons: (1) it’s good practice for clarity and for code generation, and (2) it directly ties into the command-oriented model. The `operationId` can serve as the command name the client uses. For instance, if an operation has `"operationId": "ActivateDevice"`, the client could send `{"command": "ActivateDevice", ...}` instead of method/path. Including operationId in the spec is fully supported (OpenAPI allows any alphanumeric string). The server can internally map that to the same handling as the method/path. By supporting this, we ensure the OpenAPI document itself carries the information needed for both modes of invocation. (If an OpenAPI spec from elsewhere doesn’t have operationIds, the implementer of this system might add them when adapting it for LXMF, or just use method/path calls.)

* **Error Model:** Many APIs define a generic error response schema (like a structure with an error code and message). Our system can support that as well. For example, we could have a component schema for Error with fields like `message` and `code`, and specify that 400/500 responses use that. This isn’t required by OpenAPI, but is a common pattern. We include it if it’s part of the API design, but we don’t impose a single error format – the spec can define what it wants. The minimal requirement is just that every response has a status code and maybe an error description if not 2xx.

* **Versioning and Compatibility:** We target OpenAPI 3.0 and above (including 3.1), but not older Swagger 2.0. The minimal subset is largely the same for 3.0 and 3.1, except that OpenAPI 3.1 uses full JSON Schema Draft 2020-12. Our system doesn’t fully implement that entire spec – just the basics as noted. However, if a provided OpenAPI 3.1 document uses some feature like `const` or `examples`, those can be ignored by the parser if not crucial. The goal is to not break on minor spec differences. We assume any OpenAPI definition provided for use with this system will stick to straightforward constructs.

**Unsupported or Out-of-Scope Features:**

* **Authentication Schemes:** OpenAPI supports defining `securitySchemes` (HTTP auth, OAuth2, API keys, etc.) and applying them to operations. In our system, these are unnecessary because security is handled by RNS identities and network encryption. We do not support OAuth2 flows, JWT bearer, etc. If an OpenAPI spec includes these, they would be ignored or need to be removed in the transformation. The server doesn’t perform token checking; instead it relies on identity (or out-of-band trust for who can call the API). So the `security` sections in the spec would likely be empty or just used for documentation (“this API is protected, you must have the right identity”).

* **HTTP-specific Features:** Since there is no actual HTTP protocol, concepts like headers (aside from maybe Content-Type which is implicitly JSON), cookies, CORS, etc., do not apply. For example, an OpenAPI spec might specify a custom header for an operation – our system would not use that. Similarly, things like response headers in the spec are not relevant; the response is just the JSON body in our design. Streaming responses or chunked transfer are not applicable (one message is one response).

* **Callback/Webhook and Async APIs:** OpenAPI 3 can describe asynchronous APIs, callbacks (where the server calls back the client), webhooks, etc. These are not in scope for the minimal system. All interactions are request-response initiated by the client. If a use case requires server-initiated messages (like an event push), it would be implemented as a separate mechanism, not covered by this OpenAPI mapping (or one could model it as the client polling for events via an endpoint). But we do not support OpenAPI callback objects or subscription websockets in this system.

* **Multipart/Form Data:** Only JSON payloads are supported. Endpoints that in a traditional API would accept file uploads (multipart form-data) or have form-encoded bodies are not suitable here unless they are converted to JSON (for instance, sending a file as a base64 string). The OpenAPI spec content definitions should be restricted to `application/json`. If the original OpenAPI had other content types, those would be dropped or converted.

* **Extensibility and Vendor Extensions:** Any OpenAPI extensions (`x-...` fields) are not explicitly supported unless they are irrelevant to core function. Our system doesn’t need them, aside maybe from an extension to denote the LXMF address or something (which is not standard anyway).

* **Large File Transfer:** As mentioned, sending very large data (megabytes) in a single API call is discouraged. Reticulum can do it via its file transfer utilities (like `rncp`), but within our API context, we treat it as out-of-scope. The API should be designed to either not require huge payloads or to chunk them at the application level (multiple calls).

* **Auto-Generated Client SDKs (beyond Python):** While not a spec feature, it’s worth noting that this system is geared toward Python on both ends. We are not generating multi-language SDKs from the OpenAPI (though in theory one could create a Python client class from the spec, given operationIds and schemas, to wrap the LXMF calls). The focus is on the protocol and requirements rather than tooling.

**Assumptions and Constraints:** The OpenAPI definition used with this system must be authored/tailored to respect these supported features. We assume the API designers will *limit their OpenAPI documents to the features above*. If an existing OpenAPI definition is to be transformed, it may require pruning unsupported elements. The transformation could be automated (e.g., a script to strip unsupported parts and output the minimal spec). The end result is that the clients will still see a familiar OpenAPI structure: **endpoints, methods, parameters, JSON schemas, and response codes** – providing a clear contract for usage. This enables any developer (or even automated tools) to quickly grasp how to interact with the API over the Reticulum-based messaging system.

## Assumptions and Constraints

In designing this Reticulum LXMF API system, several key assumptions and constraints have been identified:

* **Reticulum Network Availability:** We assume that a Reticulum network is in place and both clients and server are connected to it (directly or via intermediate nodes). The network can be a local LoRa mesh, a point-to-point link, or even a TCP/IP tunnel; the common factor is that Reticulum provides routing and security. The performance of the API calls will depend on this network’s bandwidth and latency characteristics (e.g., HF radio might be 300 baud with high latency, while a local Ethernet-tunneled Reticulum could be much faster).

* **Platform Compatibility:** It is assumed that all components run on Python 3 environments. Reticulum (the `rns` package) is known to run on virtually any Python-supporting platform, including small SBCs like Raspberry Pi Zero. The use of `rnspure` (pure Python implementation) can even allow running on unusual or dependency-limited systems. Thus, the client and server can be deployed on Linux, Windows, macOS, or embedded Linux devices. We constrain the design to avoid anything not available in pure Python. For example, cryptography is handled by Reticulum’s library; we don’t introduce other compiled dependencies. Memory and CPU usage should be kept low (small JSON payloads, light processing) to suit potentially limited devices.

* **Single-Message Transactions:** A hard constraint is that each request or response must fit into one LXMF message. This influences API design (no huge payloads) and is a simplifying assumption for the protocol. While Reticulum can handle large data by splitting into many packets, we choose not to split a logical API call into multiple sequential LXMF messages at the application level. This means if some data set is too large, the API should require the client to request it piecewise (like adding pagination parameters) rather than sending it all at once. It also means no multi-part upload of a single resource – each call stands alone. This constraint keeps the protocol logic simple (no reassembly needed above LXMF, no ordering issues, no partial failures to handle).

* **Compression and Encoding:** We assume both sides have enough processing power to perform compression (e.g., gzip) and decompression on the JSON payloads. This is generally true even for small devices (there are Python libraries for gzip/zlib that are efficient in C). The overhead of compression is justified by the bandwidth savings in low-speed networks. If a device were too slow to compress large JSON, that JSON is probably too large to send over its network anyway. We also assume the overhead of base64 encoding (if used) is acceptable; however, since LXMF can carry binary, we lean towards sending raw binary to avoid the 33% overhead of base64. In cases where LXMF content might be treated as text (e.g., when encoding as a URI or QR code for manual transfer), base64 might be used, but that’s optional.

* **Latency and Timeouts:** Because the network may be slow or store-and-forward, we assume that request-response cycles can take significantly longer than in typical HTTP environments. Clients and users must be aware that an API call could potentially take seconds, minutes, or even hours if nodes are offline and later come online. This is acceptable in the envisioned use cases (post-disaster communications, remote sensors, etc.), but it’s a different paradigm from instantaneous cloud APIs. The system does not guarantee real-time responses. A constraint is that usage patterns should tolerate this delay (e.g., no assumptions of immediate consistency). If synchronous behavior is needed, it is achieved at application level by waiting for the response message to arrive.

* **Reliability:** We assume Reticulum’s delivery mechanisms (acknowledgements, retries, multi-hop routing) will ensure that if there is any viable path between client and server, messages will eventually get through. Thus, we don’t implement an application layer retry except for cases of complete timeout. Reticulum’s design provides a robust foundation, but it’s not infallible; extreme conditions might drop messages. The application should be prepared to retry if no response is received in a reasonable timeframe. However, duplicate detection (via req\_id) ensures that if a late/duplicate response arrives, the client can ignore it if it has already processed that request.

* **Propagation Nodes for Offline Delivery:** As part of assumptions, we consider that LXMF Propagation Nodes may be deployed in the network to buffer messages for offline endpoints. This greatly aids the API usage pattern: a client can send a request even if the server is offline; a propagation node will store it and deliver when the server comes online. Similarly, the server’s response will be stored if the client is offline. This decoupling is powerful but introduces uncertainty in response times. The design assumes such infrastructure exists or the network is direct – it doesn’t change our protocol, but it’s an assumption about deployment that justifies not having the client and server simultaneously active or connected.

* **OpenAPI Document Size and Complexity:** We assume the OpenAPI definitions used are of moderate size and complexity, suitable for constrained use. For example, an API with perhaps tens of endpoints, not hundreds. The minimal subset approach inherently trims the size. If an OpenAPI has lots of verbose description or unused components, we expect those to be removed. Also, deeply nested or complex schemas (especially ones heavy in anyOf/oneOf logic) are assumed to be simplified for this context. The focus is on practical data models rather than exhaustive schema tricks.

* **No External Dependencies at Runtime:** Beyond the Reticulum (`rns`) and LXMF (`lxmf`) libraries, plus standard Python libraries (json, zlib, etc.), we assume no need for heavy frameworks. This keeps the system lightweight. For instance, we are not running a Flask or FastAPI server – instead, the server is a custom loop on LXMF. This is a conscious choice due to the unique transport and the desire to minimize overhead.

* **Autonomy and Decentralization:** A philosophical assumption of Reticulum is no centralized coordination. In our API context, this means there is no centralized registry of services or clients. Everything is ad-hoc and peer-to-peer. The API server is autonomous; the client reaches it via its address. We do not rely on DNS, service discovery protocols, or certificate authorities. Trust is established by exchanging identity keys directly (out-of-band or via the network’s built-in mechanisms).

* **Data Consistency and Transactions:** Given the stateless, message-oriented nature, we assume that complex transactions (in the database sense) or sequences of dependent calls may be harder to achieve. If an API operation requires multiple back-and-forth steps, that would violate our one-message rule. So each operation should ideally be atomic and self-contained. If a series of actions is needed, the client might call them sequentially (with each call confirmed before the next). This is more a design guideline for API creators: try to design coarse-grained operations that do a lot in one call, rather than requiring chatty fine-grained operations which would be inefficient.

* **Testing and Debugging:** We assume developers will test this system in controlled conditions (e.g., on a LAN or simulation) before deploying on slow links. Debugging across such an asynchronous system can be tricky. It might be useful to have a flag to print or log all JSON messages for debugging. This could be included as an implementation note: while not a requirement, it is recommended to incorporate good logging.

In conclusion, within these assumptions and constraints, the Reticulum LXMF-based API system aims to offer a **secure, portable, and efficient API layer** on top of a resilient mesh network. By carefully limiting the scope of OpenAPI features and optimizing every aspect for low bandwidth, we ensure the system remains **comprehensive but lightweight**, enabling interoperability in environments where conventional web APIs would be impractical or impossible. The above requirements and design choices provide a foundation for developers to implement both server and client software that meet these goals, effectively bringing RESTful API capabilities to the world of opportunistic, off-grid networks.

**Sources:**

* Reticulum & LXMF documentation and README (for protocol structure, security, and low-bandwidth operation)
* API7 OpenAPI 3.0 summary and OpenAPI Specification 3.0.3 (for OpenAPI features and usage of JSON Schema, status codes)
* Unsigned.io Reticulum Manual (for Reticulum network capabilities and Python platform support)

