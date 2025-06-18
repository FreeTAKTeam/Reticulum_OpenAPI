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

All API messages use a **JSON-based payload** to represent the request or response data, which is then *compressed and encoded* for transport via LXMF. JSON provides a universal, human-readable structure for parameters and data, while compression (e.g. using DEFLATE or a similar algorithm) significantly reduces message size to suit bandwidth constraints. The compressed JSON is placed into the LXMF message payload (the *Content* field) as a binary blob, . LXMF messages themselves are structured as a timestamp plus content, title, and fields sections; this design allows flexibility. In this system, we propose using the **Content** section for the main JSON payload, and the optional **Fields** dictionary for any additional metadata that aids in routing or interpretation (if needed). Each message’s *Title* field may be left empty or used for a brief human-readable description (not strictly required for operation).

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
