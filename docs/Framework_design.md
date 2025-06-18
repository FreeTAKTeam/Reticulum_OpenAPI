# Reticulum OpenAPI Asynchronous Framework Design Specification

## Architecture Overview
![image](https://github.com/user-attachments/assets/56a70d0b-14f7-45e8-988b-abafa3a4226f)


The Reticulum OpenAPI framework is a **fully asynchronous, lightweight Python server-client system** built on the Reticulum network stack and its LXMF messaging protocol. It is designed to operate efficiently on edge devices like Raspberry Pi, leveraging Reticulum’s low-overhead, delay-tolerant communication suitable for low-bandwidth links. The framework uses a modified **Model-Controller-Service (MCS)** architecture (inspired by NestJS) to separate concerns and improve maintainability. Key characteristics of the architecture include:

* **Async Server and Client:** Both server and client components are implemented with `asyncio` to handle I/O without threads, ensuring low resource usage and scalability on constrained hardware.
* **Reticulum + LXMF Messaging:** All communication uses LXMF messages over Reticulum. The LXMF *Fields* dictionary is used to route API commands, and the *Content* section carries the request/response payloads. This allows the system to function similar to a REST API but on a mesh/off-grid network.
* **Schema-Driven Models:** Data models for messages are defined by JSON schemas and auto-generated into Python dataclasses. This ensures that all message content adheres to a well-defined schema, enabling validation and consistent interpretation on both server and client.
* **MCS Layering:** The framework is organized into Models (data schemas and ORM), Controllers (async endpoint handlers), and a Service layer (message routing and network interface). This modular design allows logical separation of concerns, improving code reusability and clarity.
* **Extensibility:** While focusing initially on command-style messaging, the design anticipates future extensions – for example, adding an HTTP REST interface or other transport services – without significant changes to core logic. The architecture permits multiple service adapters (LXMF, HTTP, etc.) to coexist and reuse the same controllers.

Overall, the system acts as an **async microservice** on a Reticulum mesh network, processing incoming LXMF command messages and returning responses. It emphasizes **low latency, non-blocking I/O**, and minimal overhead so that even battery-powered or CPU-limited devices can host or interact with the API.

## Component Responsibilities (Model, Controller, Service)

The framework follows a clear division of responsibilities among the **Model**, **Controller**, and **Service** components, analogous to a NestJS-like layered architecture. This separation ensures that each component has a single focus, which simplifies development and testing and promotes clean code organization. Below we detail each component’s role:

### Model Layer (Data Schema & Persistence)

Models define the data structures and persistence logic of the application. In this framework, models have two parts:

* **Data Transfer Models:** Python dataclasses generated from JSON Schema or OpenAPI definitions represent the structure of API messages. Each dataclass corresponds to a request or response schema for a particular command/endpoint. These are lightweight plain dataclasses (or Pydantic models, if validation is needed) that enforce types and facilitate JSON (de)serialization. By auto-generating them from schemas, we ensure **schema-based validation** — incoming JSON content can be validated against the schema and parsed into a dataclass, guaranteeing it conforms to the expected format.
* **ORM Persistence Models:** For any persistent data (e.g. configuration, user records, sensor readings), the framework uses SQLAlchemy ORM models. These are classes mapped to database tables (SQLite or other SQL databases) that allow storing and querying data. The ORM models encapsulate how data is saved or retrieved, whereas the dataclass models encapsulate the in-message representation. In many cases, the structure of a dataclass will mirror an ORM model for convenience, but they serve different purposes (one for messaging, one for storage).

**Key responsibilities of the Model layer:**

* Define **dataclass schemas** for all API message types (requests and responses). This can be automated by a code generator that reads JSON schema files and produces `@dataclass` classes with appropriate fields and types. These dataclasses may include basic validation (via type hints or Pydantic if used) to ensure data integrity.
* Perform **validation of incoming data** against the JSON schema. The framework should integrate a JSON Schema validation step (using a library like `jsonschema`) or rely on dataclass/Pydantic validation to reject malformed messages. This guarantees the server only processes commands with expected fields and types, as defined in the protocol spec.
* Manage **database access** through SQLAlchemy models. If a controller needs to create or fetch persistent data, it will use the ORM models. The Model layer should handle creating database sessions (using SQLAlchemy’s async session for non-blocking DB operations) and may include helper methods for common queries or updates.
* Ensure that model definitions are **consistent across server and client**. The same JSON schemas used to generate server dataclasses are also used by the client for its dataclasses, making the client “schema-aware.” This consistency means a client can construct a request as a Python object and be confident it matches what the server expects, and vice versa for responses.

*Example:* A JSON schema for a command `AddNode` might define fields like `node_id` (string) and `location` (object with coordinates). The code generator produces a `@dataclass AddNodeRequest` with `node_id: str` and `location: Location`. Similarly, an `AddNodeResponse` dataclass could be generated. The ORM might have a `Node` model for persistent nodes in a table. The controller can easily convert between the dataclass and ORM model (e.g., create a `Node` entry from an `AddNodeRequest`).

### Controller Layer (Async Endpoint Handlers)

Controllers are the **business logic handlers** for API endpoints. Each controller is an async Python class that groups related endpoints (similar to a controller in NestJS). Within a controller, each API endpoint (or command) is implemented as an asynchronous coroutine method. These methods define what happens when a particular command message is received.

**Characteristics and duties of controllers:**

* **One coroutine per endpoint:** Each public API command corresponds to a method like `async def <command_name>(self, request: RequestType) -> ResponseType`. For example, a `NodeController` might have `async def add_node(self, req: AddNodeRequest) -> AddNodeResponse`. This method executes whatever logic is needed to fulfill the command – e.g., validating the request, interacting with the database via models, and then returning a result or status.
* **Routing key based dispatch:** Controllers do not themselves listen on the network; instead, the Service layer will route incoming messages to the correct controller method based on the command name (more on routing below). Controllers thus focus only on handling the *content* of the message, not how it arrived.
* **Validation and error handling:** Upon being called, a controller method can assume basic validation has been done (since the payload was already parsed into a dataclass). It may still perform additional checks (business rules, permission, etc.). If something is wrong (e.g., required data is missing or a database error occurs), the controller should raise an appropriate exception or return an error response object. The framework can define standard exception types or error response schemas so that errors are consistently communicated.
* **Business logic execution:** The controller implements the core logic for the command. This could involve computations, database CRUD operations, or calling external services. All such operations should be awaited if they are I/O-bound. For example, `add_node` might store the new node in the DB (async DB call) and maybe trigger a background task. Controllers can call other Python services or utilities as needed; if the project grows, some logic could be moved to separate service classes (in the business-logic sense) which the controller calls. However, in our MCS context, the “Service” component refers to the network service, not business services.
* **Return response:** The controller coroutine returns a response dataclass (or perhaps a simpler ack/status). The returned value will be serialized by the Service layer into an LXMF message to send back. If no response is required for a given command (one-way notification), the controller might return None or simply complete – but the framework protocol by default focuses on request/response style, so most commands will have a reply.

Controllers are **organized by domain or feature.** This modular grouping (similar to NestJS modules) makes it easy to enable/disable or extend features. For instance, a `SensorController` could handle commands like `GetSensorData`, `SetSensorThreshold`, etc., whereas a `ManagementController` handles admin commands. This keeps code organized and allows easy addition of new controllers for new API areas. To register a new controller with the system, a developer will implement the class and then inform the Service layer about it (see startup example below).

**Summary of Controller responsibilities:**

* Implement **async endpoint handlers** for each API command, encapsulating the action to perform.
* Use **dataclass models** as input parameters and return types, to enforce schema compliance in logic.
* Interact with the **Model/ORM** layer for data persistence or retrieval.
* **Do not manage networking** – controllers are unaware of LXMF details like addresses or signatures. They operate at the application logic level.
* Handle any **exceptions or edge cases**, possibly mapping them to error responses (the framework can catch exceptions from controllers and convert to error messages automatically).

### Service Layer (LXMF Message Bridge)

The Service layer is the **bridge between the Reticulum/LXMF network and the controllers.** It is an asynchronous service responsible for receiving LXMF messages, decoding them, routing them to the appropriate controller method, and sending back responses. This component can be thought of as analogous to the HTTP server in a typical web API, except it speaks LXMF over Reticulum instead of HTTP over TCP. It encapsulates all message-handling mechanics so that controllers can remain agnostic of the network.

**Core responsibilities of the Service layer:**

* **Reticulum Initialization:** On startup, the service initializes a Reticulum context (using the RNS library). This involves loading or generating a cryptographic identity for the server and configuring Reticulum interfaces (e.g., a TCP link for testing, or LoRa radio, etc., as specified in the Reticulum config). The service may create one or more **Destinations** (RNS destination endpoints) that represent the “addresses” at which it will receive LXMF messages. For example, the server might define a static destination hash or name (like “ReticulumOpenAPIService”) so clients can send to it. Reticulum’s zero-conf routing will ensure messages addressed to that destination are delivered to the service if reachable.
* **LXMF Node & Inbox:** The service sets up an LXMF node or subscriber to handle incoming messages. Using the LXMF library, it will open an **inbox** or register a callback for new messages. When a message arrives (from any Reticulum interface), the service asynchronously handles it. Each LXMF message includes a *Content*, *Title*, and *Fields* as described in the LXMF spec. In this framework, we expect the *Fields* dictionary to contain routing information (at minimum, the command name), and the *Content* to contain the message payload (likely as JSON text or a binary encoding of the JSON).
* **Message Routing:** Upon receiving a message, the service inspects the LXMF Fields to determine which controller and endpoint should handle it. For example, the Fields might include a key like `"command": "add_node"` (or a more namespaced value such as `"node.add"`). The service maintains a registry or mapping of command names to specific controller coroutine functions. This mapping is established during the application startup when controllers are registered. Using the command key, the service looks up the target handler. If no matching command is found, the service can return an error response (e.g., an “Unknown command” error).
* **Payload Decoding:** The LXMF Content (which for our API is likely a JSON string or bytes) is decoded into a Python object. Typically, the content will be JSON text, which is parsed into a dictionary. The service knows which dataclass schema corresponds to the command (for instance, `AddNodeRequest` for `"add_node"` command). It will then convert the JSON/dict into the appropriate dataclass object – either by calling the dataclass constructor or using a library function. If the content fails validation (e.g., required fields missing, types mismatch), the service will generate a validation error response (possibly using the JSON schema error messages).
* **Invoke Controller:** Once the request payload is prepared as a dataclass instance, the service calls the corresponding controller method coroutine, using `await`. This call is done in an **non-blocking** manner – the service itself is an async function handling the message, so awaiting the controller allows other tasks (like receiving other messages) to proceed. If many messages arrive concurrently, the service can spawn separate tasks for each message to handle them in parallel (depending on concurrency needs and hardware capacity).
* **Send Response:** When the controller returns, the service takes the response (likely a dataclass or simple type) and encodes it into an LXMF message back to the origin. The origin address (the LXMF Source of the incoming message) is used as the Destination for the reply. The service constructs a new LXMF message object, placing the response data into the Content field (JSON-serialized), and using the Fields for any routing metadata needed for the response. Typically, the response Fields might include the original command name (or a variant indicating it's a response) and a correlation ID. In a request-response pattern, the service should utilize a **correlation identifier** so the client can match replies to requests. This could be a unique ID generated by the client for each request (included in request Fields as `req_id`, for example) that the server simply copies into the response Fields. The framework will define a convention for this, ensuring every request’s Fields contains an ID and every response echoes it back.
* **Error Handling:** If the controller raises an exception or returns an error, the service catches it and crafts an error response message. For instance, the Fields might include an `"error": true` flag or an error code, and the Content might contain an error details object (with fields like `message` and `code`). This way, the client can distinguish successful responses from errors. The service might have a generic exception-to-error converter (mapping certain Python exceptions to meaningful API error codes).

In effect, the Service layer operates like an **async message router and dispatcher**. It hides all the Reticulum/LXMF specifics (signatures, addressing, etc.) from the rest of the application. This layer would likely run in an endless asyncio loop (or background task) waiting for incoming messages. It could also manage periodic tasks if needed (for example, sending heartbeat messages or processing retries if using propagation nodes for store-and-forward).

**Key features of the Service layer:**

* **Async message handling:** Uses `asyncio` event loop to listen for messages and handle them without blocking. Each incoming message can be handled in its own coroutine, allowing multiple simultaneous requests to be processed on multi-core systems efficiently.
* **Lightweight and edge-friendly:** Avoids heavy protocols; uses minimal framing (just LXMF). Reticulum handles encryption and delivery, so the service code focuses only on application logic. This keeps the memory and CPU footprint low (Reticulum + a simple async loop), appropriate for devices with limited resources.
* **Registration of handlers:** Provides an API to register controllers or individual command handlers. For example, during startup the application might call `service.register_controller(NodeController())`, and the service will introspect or use a predefined mapping to associate `"add_node"` command with `NodeController.add_node` coroutine.
* **Decoupling:** The service is decoupled from specific controllers; it references them via an interface (e.g., an abstract base class or simply through the mapping). This decoupling means new controllers can be added or a different transport service can reuse the controllers.

## Message Routing Mechanism

Message routing in the Reticulum OpenAPI framework determines how incoming LXMF messages are directed to the correct controller endpoint and how responses find their way back to the sender. It leverages the LXMF message structure – particularly the **Fields dictionary for routing metadata and the Content for payload** – to emulate a request/response API on top of an asynchronous, store-and-forward network.

### Command Encoding in LXMF Fields

Each API request message must carry an indication of which command or endpoint it is invoking. We achieve this by inserting a **command identifier** into the LXMF Fields dictionary of the message. For example, a Fields might look like:

```json
Fields = {
  "command": "add_node",
  "req_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

* The `"command"` key (name can be decided, e.g., `cmd` or similar) tells the service which controller method to call. This could be a simple name or a composite identifier. If we use simple names, they should be unique across the whole API. Alternatively, namespacing can be used (e.g., `"node.add"` vs `"user.add"` to avoid collisions and group by controller).
* The `"req_id"` is a unique request ID, generated by the client for each request. It’s a UUID or similar random string. The server does not need to interpret it; it will just propagate it to the response. This ID allows the client to correlate the asynchronous response to the original request.

Other potential fields for future or advanced use:

* A `"type"` or `"msg_type"` field to distinguish requests from responses or to indicate a subtype of message. For instance, `type: "request"` vs `type: "response"` (though this may be redundant if we have separate handling based on presence of certain fields).
* A version field if we plan to version the API or schema (`"schema_ver": 1.0`).
* Fields for quality-of-service, priority, or other routing hints if needed by LXMF propagation (not typically needed unless using advanced LXMF node features).

For **response messages**, the routing works similarly but in reverse:

* The destination of the response is the original sender (as obtained from the LXMF *Source* of the request).
* The Fields of the response message include the same `req_id` from the request, and possibly a `"command": "add_node"` as well (to let the client know which command this is the result of, in case the client supports out-of-order processing or debugging). The response could also set a flag like `"response": true` or use a different field such as `"status": "ok"` or `"status": "error"` to indicate success or failure.

Using LXMF Fields for routing keeps the routing information at the metadata level (not in the content), which is appropriate because it’s not part of the business data but the protocol. LXMF’s design allows the Fields dictionary to be arbitrary and nested, so we have flexibility to add more keys as needed for routing or protocol evolution.

**Example message routing flow (Command Request):**

1. **Client sends request:** The client constructs an `AddNodeRequest` dataclass with the necessary data, serializes it to JSON, and creates an LXMF message. The Fields might include `{"command": "add_node", "req_id": "ABC123"}`. The message is addressed to the server’s LXMF destination (the client either knows the destination hash or uses a shared name that Reticulum can resolve).
2. **Server receives message:** The service’s LXMF inbox yields the message. The service reads Fields:`command = "add_node"`, `req_id = "ABC123"`.
3. **Lookup handler:** The service finds that `"add_node"` maps to the method `NodeController.add_node`. It retrieves the JSON content from the message, and parses it into an `AddNodeRequest` object (using the schema).
4. **Dispatch to controller:** The service awaits `NodeController.add_node(request_obj)`. Meanwhile, it may log the event or handle multiple messages concurrently.
5. **Controller processes:** Suppose the controller creates a new Node in the DB and returns an `AddNodeResponse` with a success status and maybe an assigned node ID.
6. **Prepare response:** The service takes the `AddNodeResponse` object, serializes it to JSON. It then creates a new LXMF message with Content = that JSON, and Fields containing at least `req_id = "ABC123"` (copied from request) and possibly `"command": "add_node"` (for clarity, though not strictly required).
7. **Send response:** The service signs and sends the LXMF message. Reticulum routes it back to the original sender’s address.
8. **Client receives response:** The client’s LXMF listener (similar mechanism) picks up the incoming message. By looking at Fields, it matches `req_id` "ABC123" to an outstanding request promise/future. The content is parsed into an `AddNodeResponse` dataclass, delivered back to the code that made the request.

**Handling Unknown Commands:** If the server gets a message with a `command` that is not registered, it should reply with an error. For example, it could send back Fields `{"req_id": "...", "error": "UnknownCommand"}` and a Content that might contain an error message JSON (or possibly no content, depending on design). This ensures that the client isn’t left waiting indefinitely; it will receive a response for every request, even if that response is an error.

**Routing Table Implementation:** Internally, the service can implement routing as a dictionary, e.g.:

```python
handlers = {
   "add_node": node_controller.add_node,
   "get_status": management_controller.get_status,
   ...
}
```

This dictionary is populated during startup when controllers are registered. The keys are command strings and values are coroutine functions (already bound to controller instances). The service simply does `handler = handlers[command]` to retrieve and call the function.

Alternatively, one could implement a decorator on controller methods, e.g. `@command("add_node")` that registers the function in a global registry. Either approach is acceptable; the specification doesn’t mandate how, only that the mapping must be set up reliably.

**Use of LXMF Title:** We have not assigned a role to LXMF’s *Title* field in this framework. LXMF Title is an optional short title or subject for the message. We could repurpose it for something (for example, a short human-readable summary of the command for logging, or a message type identifier). However, for now, the design doesn’t require using Title – the Fields cover our routing needs, and the Content holds the actual data. Title can be left empty or used for debugging (e.g., setting Title = command name as well, so that any LXMF tooling that lists messages shows the command in the title).

### Asynchronous Request Handling

The routing mechanism is inherently asynchronous. Multiple requests can be in flight concurrently:

* The server can process several incoming LXMF messages in parallel if needed. Because each controller method is an `async def`, the service can `await` one without blocking the acceptance of another. If Reticulum/LXMF delivers messages one by one, the service might internally create an `asyncio.Task` for each message to allow simultaneous processing. The design should ensure thread-safety for shared resources (which is simpler in asyncio since code runs in one thread by default). If using an async database session per task, for instance, each can operate independently.
* The client can also have multiple outgoing requests at once. The `req_id` correlation handles this: e.g., client sends out requests with IDs A, B, C before responses come back. The server will reply, echoing those IDs. The client’s routing logic will match responses to the correct request future or callback. This allows a **non-blocking, pipeline** usage of the API from the client perspective.

**Timeouts:** Because mesh networks can be slow or unreliable, the client (or server, if waiting on something) should implement timeouts. For example, a client request could `await` a response with a timeout of N seconds; if none arrives, it can assume the request failed or was lost. The framework should make it easy to set a default timeout for requests. Similarly on server side, if a controller calls out to an external system and that hangs, using `asyncio.wait_for` can prevent one request from never completing.

In summary, message routing uses a **command-based addressing scheme** within LXMF Fields to direct messages to code, enabling a pattern similar to RPC or REST but over the Reticulum decentralized network. This design cleanly separates the transport (Reticulum addressing and LXMF delivery) from the application logic (command handling in controllers).

## Async Design Patterns and Considerations

The entire framework is designed around Python’s asynchronous programming model to maximize concurrency and keep the system lightweight. Here we outline the key async design patterns and how they are applied in the Reticulum OpenAPI project:

* **Event Loop and Async IO:** The server runs an `asyncio` event loop (for example, using `asyncio.run(main())` in the startup script). The main tasks on this loop are listening for LXMF messages, handling incoming messages, and possibly other periodic tasks. All I/O operations – receiving data from Reticulum, database queries, sending responses – are awaited, allowing the event loop to remain responsive. This non-blocking approach is crucial for running on edge devices; it avoids the overhead of multi-threading and context switching, and it lets one small CPU handle many tasks by interleaving them.

* **Async LXMF Integration:** Reticulum’s Python API and the LXMF library calls are integrated in an async manner. If the LXMF library provides callbacks (e.g., calling a function when a message arrives), the service will likely translate that into an asyncio coroutine call. For example, a callback could do `asyncio.create_task(service.handle_message(msg))` to hand off the message to the async handler. In case the LXMF library doesn’t directly support asyncio, one pattern is to run the LXMF listening in a separate thread or use an executor, then forward messages to the async loop via thread-safe queues. However, since LXMF and RNS are Python-based, we can likely integrate them without extra threads by using non-blocking sockets or periodic polling in the event loop. This is an area for careful implementation, but the goal is **zero blocking calls** on the main thread.

* **Task Scheduling:** The framework should leverage asyncio tasks for concurrency. When the Service layer receives a message, it can spawn a task for processing it if we expect overlapping workloads. For instance:

  ```python
  async def on_message(msg):
      # parse header
      task = asyncio.create_task(handle_request(msg))
      # allow this function to continue listening while task runs
  ```

  The `handle_request` coroutine (which invokes controller and sends reply) then runs concurrently. This pattern prevents one long-running handler from blocking others. It’s particularly useful if some commands are slow (e.g., doing a large database operation) while others are quick – they won’t bottleneck each other.

* **Async Database Access:** With SQLAlchemy, we will use the async ORM engine (SQLAlchemy 1.4+ supports `asyncio`). That means database queries like `await session.execute(...)` and `await session.commit()` can yield control while the I/O (disk or network, in case of remote DB) is in progress. This avoids stalling the event loop during DB operations. The framework will likely have an async session per request (perhaps created in a dependency or at handler start) to avoid contention. If using SQLite on a Pi, the async driver will internally use a thread, but from our perspective it’s `await`able. This ensures that even persistence is done asynchronously.

* **No Blocking Calls:** A strict rule is that no controller or service code should call blocking functions without moving them off the main thread. Blocking calls could be CPU-bound computations or synchronous I/O. For CPU-bound tasks (e.g., image processing, heavy encryption beyond what RNS does), the framework should offload to a worker thread or process (using `asyncio.to_thread` or a process pool). For now, typical operations (parsing JSON, minor computation) are fine to do inline, but anything that might take significant time should be encapsulated so it doesn’t freeze the loop.

* **Async Client Behavior:** The client side is also asynchronous. It might expose an API like `await client.send_request(cmd, data)` which returns when the response is received (or timeout). Under the hood, it likely also uses an event loop (the same `asyncio` framework). If the client is running in an application that already has an event loop (e.g., an asyncio-based UI or service), it should integrate by creating tasks for requests and awaiting them. We ensure that even client-side Reticulum operations (sending message, waiting for reply) are non-blocking. For example, sending a message might involve writing to a socket – the Reticulum library should be doing that asynchronously (if not, again it can be run in an executor).

* **Parallelism and Ordering:** Async IO ensures that tasks can run in parallel (concurrently). We must be mindful of data races or ordering issues:

  * Within a single request handling, operations are sequential (we use `await` to ensure, say, the DB write is done before sending a response).
  * Across different requests, there’s no guaranteed order – which is fine, as each request is independent. However, if two messages from the same client come in quick succession, they might be handled out of order relative to sending if not carefully managed. LXMF itself doesn’t guarantee order of delivery in a strict sense (especially if messages are routed differently), so our system should not assume in-order delivery. If ordering is needed for certain sequences, that would be an application-level concern (not in scope for initial design).

* **Long-running tasks:** If a controller needs to perform a long action (say a firmware update process that takes minutes), the async pattern would be to kick off a background task and immediately return a response like “accepted” with maybe a task ID. The framework can handle quick responses easily; for such long tasks, we wouldn’t tie up the request waiting. This is more of a higher-level design note: initially, we focus on request/response where response is quick. But the design (with async and ability to spawn tasks) can handle fire-and-forget jobs or delayed responses if needed.

* **Resource Cleanup:** When the server shuts down (or the client), we should properly close resources. The async context can handle graceful shutdown by cancelling tasks and closing the Reticulum interface. For example, if the service uses a persistent connection (like TCP link to another node), we ensure it’s closed. Also, database sessions should be closed. We might use the Python `asyncio.Signal` handling or context managers to catch termination signals and initiate a shutdown sequence, awaiting all outstanding tasks. This prevents resource leakage or corrupted state.

**Efficiency on Edge Devices:** Using asyncio rather than multi-threading is not only simpler in Python, but also lighter on memory – important for devices like Raspberry Pi. The single-threaded async model avoids the overhead of thread stacks and context switches. Additionally, Reticulum’s design (being optimized for even embedded use) aligns with this: we run a single network thread of control. Real-world use of Reticulum on Raspberry Pi has shown it can run background services even in adverse conditions, so our async framework builds on that foundation.

**Concurrency example:** Suppose a Raspberry Pi-based server receives 10 sensor read commands at once. The service will create 10 tasks, each task will perhaps do a small DB read (non-blocking) and return data. All 10 can be awaiting I/O simultaneously, and as results come, they send responses. This maximizes throughput. If this were done with threads, the context switching could overwhelm a small CPU, but async keeps it manageable.

In summary, the framework adopts Python’s modern async features throughout, ensuring that it can handle multiple operations concurrently without hogging system resources. This makes it scalable (handle more clients/messages) and efficient (only does work when there is work, otherwise idle), which is ideal for the unpredictable, sometimes low-bandwidth environment of mesh networks.

## Client Implementation Guide

The client side of the Reticulum OpenAPI framework is a mirror image of the server in many respects – it’s simpler, but it must also use the Reticulum and LXMF stack asynchronously and be aware of the data schemas. The client is essentially an **async API requester** that packages commands into LXMF messages and handles responses. This section outlines how to implement and use the client.

### Client Architecture

A typical client will consist of:

* An instance of the Reticulum LXMF interface (identifiable by its own Identity/Address on the network).
* A set of generated dataclass models (the same as the server’s models for requests and responses).
* A lightweight **Client Service** that can send a request and wait for a response (possibly reusing some of the same library code as the server’s Service, but configured for the client role).
* Optionally, convenience methods corresponding to API commands for ease of use.

### Initializing the Client

Before sending requests, the client must initialize the Reticulum context:

1. **Reticulum Setup:** The client loads a Reticulum config or uses defaults. For initial testing with TCP, the client’s config will have a TCP interface pointing to the server’s node (or a static hub). On startup, the client creates a Reticulum identity (if not already present) so it has a source address. This could be done via `RNS.Reticulum()`, similar to the server.
2. **LXMF Node:** The client either runs an LXMF daemon in process or uses the LXMF library to open its own mailbox. It needs to listen for incoming LXMF messages *because responses from the server will come as LXMF messages addressed to the client*. This can be set up with a callback or loop just like on the server. Essentially, the client is also a mini-service for handling responses.
3. **Schema Loading:** The client imports or generates the same dataclass definitions for requests and responses. Because these are generated from a common schema, the client and server share these message formats. This means the client can easily construct a request object and validate it locally (helping catch errors early), and also parse the response into an object to work with in code.

### Sending a Request (Usage Pattern)

The framework should provide a high-level client API. For example, it might look like:

```python
client = OpenAPIClient(destination=server_address)  # initialize client with server destination
req = AddNodeRequest(node_id="node123", location=Location(x=1.2, y=3.4))
try:
    resp = await client.send_request("add_node", req)
    # resp would be an instance of AddNodeResponse
    print("Added node, assigned ID:", resp.assigned_id)
except TimeoutError:
    print("No response from server, request timed out")
except ValidationError as e:
    print("Server responded with error:", e)
```

Important aspects of the client request flow:

* The client likely has the server’s address or callsign. This could be configured (e.g., a known hash or obtained via a discovery process). For now, assume it’s known – perhaps the server shares its identity key or a named address out-of-band.
* `send_request(command, data_obj)` will internally do:

  * Serialize `data_obj` to JSON (or MsgPack, but JSON is easier for debugging).
  * Create an LXMF message with `Destination = server_address`, `Content = JSON`, and `Fields = {"command": command, "req_id": generated_id}`.
  * Send the message via RNS/LXMF. The sending should be `await`able (the library might provide an async send or we wrap it in `to_thread` if needed).
  * Simultaneously, prepare to receive the response. The client will likely store a `Future` or `Event` in a dictionary keyed by `req_id`. It then waits on that future with a timeout.
* **Response handling:** The client’s LXMF listener (running in background) will trigger when any message arrives. When a message comes:

  * Check if it’s a response (maybe by seeing if the `req_id` matches one of our pending requests).
  * If yes, cancel the timeout future and set the result. The listener will parse the Content into the appropriate response dataclass. It knows which type by either looking at the command in Fields or by having stored the expected response type when the request was sent. For example, the `send_request` function might know that for command "add\_node", the expected response schema is `AddNodeResponse`, so it will use that class to parse.
  * If the response Fields indicate an error (e.g., contains `"error": "...") or if the content fails schema validation, the client can raise an exception (like `ValidationError`or a custom`APIError\`) to the caller.
* The future is set with either the response object or an error, and `send_request` then returns/unblocks. This design allows the **client code to simply await the call** and get the result, abstracting away the network details.

The client should also handle cases like:

* **Timeouts:** If no response arrives within a configurable timeout, the future is never set. We should use `asyncio.wait_for` or similar to raise a `TimeoutError` in that case, so the calling code knows the request didn’t complete. The pending future can then be discarded.
* **Server unreachable:** If Reticulum immediately knows the destination is unreachable (not likely, since it might just store and try later), the send operation might fail. We should catch exceptions from send and propagate an error to the user.
* **Multiple requests:** The client can issue multiple `send_request` calls concurrently (each with its own `req_id` and future). The listener will differentiate responses by `req_id`. This concurrency should be supported naturally by the design.

### Example: Defining and Using a New Command

Suppose the API is extended with a new command `GetNodeStatus` that asks the server for status of a node. Here’s how a developer would add this on the client side (after doing so on server):

1. **Schema**: A JSON schema for `GetNodeStatusRequest` and `GetNodeStatusResponse` is added (e.g., request might have `node_id`, response might have `status` and `last_seen`).
2. **Dataclass generation**: Running the codegen tool produces `GetNodeStatusRequest` and `GetNodeStatusResponse` classes (dataclasses).
3. **Client usage**: The developer can then do:

   ```python
   req = GetNodeStatusRequest(node_id="node123")
   resp = await client.send_request("get_node_status", req)
   print("Node status:", resp.status, "last seen:", resp.last_seen)
   ```

   No other changes needed on client side, because `send_request` is generic. Optionally, the client library might offer a convenience method, e.g., `await client.get_node_status("node123")` that internally creates the request object. Such sugar can be generated or manually added for frequently used commands.

### Running the Client

To run the client application:

* Ensure that the Reticulum network is running or configured (for testing, the server and client could both run Reticulum with a TCP link connecting them).
* Start the client’s asyncio loop. Possibly, the client runs as part of an interactive script or a small app. It might not need to run forever; it can send a request then exit. But if it needs to receive asynchronous notifications or multiple responses, it will keep the loop alive.
* The client should also register a handler for incoming messages if it expects unsolicited messages (not common in request/response, but possible extension: server pushes an update to client). In this initial model, client only expects responses to its requests, so the logic is simpler.

**Client on Edge Devices:** The client code can also run on constrained devices (like a Raspberry Pi or even something like an ESP32 running MicroPython reticulum, though our Python code assumes CPython). Because it uses the same async principles, a client on a Pi can happily communicate over LoRa or other low-bandwidth mediums. The underlying Reticulum will handle buffering and retries; the client just awaits the eventual response.

**Security:** By default, Reticulum and LXMF provide encryption and authentication. The client should manage its identity keys securely (Reticulum will have created them). When the client sends a message, it’s signed by its identity, and the server can verify authenticity. The user of the client library doesn’t have to add extra encryption; it’s handled by Reticulum (the identities and link keys). However, clients should be aware to import the server’s identity (if required for addressing or if using any trust-based routing). In many cases, just knowing the destination hash is enough because Reticulum can route based on hash without prior exchange (albeit without knowing the public key until contact).

### Schema Awareness and Validation

One major advantage of the client being schema-aware is that it can validate data both ways:

* When constructing a request dataclass, if required fields are missing or types are wrong, a dataclass or Pydantic model can throw an error even before sending, preventing a faulty message from going out.
* When receiving a response, the dataclass parsing will ensure the data matches expected types (if the server sent something unexpected, the client might log or raise an error indicating a protocol mismatch).

This keeps the client and server in lockstep regarding the protocol. As the schemas evolve, running the generator to update dataclasses on both sides ensures neither is out of date.

### Minimal Client Example (Pseudo-code)

To illustrate all the above, here is a pseudo-code outline of a minimal client using the framework:

```python
import asyncio
from reticulum_client import OpenAPIClient  # hypothetical client class from our framework
from models import AddNodeRequest  # import generated dataclass

async def main():
    # Initialize client (this sets up Reticulum and LXMF listening)
    client = OpenAPIClient(server_dest="XXXXX...")  # use server's destination (hash or name)

    # Construct request object
    request = AddNodeRequest(node_id="node123", location={"lat": 10.0, "lon": 20.0})

    # Send the request and await response
    try:
        response = await client.send_request("add_node", request)
    except Exception as e:
        print("Request failed:", e)
    else:
        print("Server response:", response.status, response.assigned_id)

    # Optionally, close the client (which would close network interfaces)
    await client.close()

# Run the client main
asyncio.run(main())
```

This example would handle under the hood all the complexity of message formatting, sending, and waiting for reply. The user of the client API only deals with Python objects (requests and responses), making it high-level and easy to integrate into other applications.

## Deployment and Testing Considerations

Designing for deployment and testability is crucial, especially given the edge-focused use cases and the need for reliability in mesh networks. This section covers how to deploy the server, how to test the components (both unit tests and integration tests), and other operational considerations.

### Deployment on Edge Devices

* **Dependencies and Environment:** The framework should be kept lightweight in terms of dependencies. It will require the `rns` (Reticulum) and `lxmf` Python packages, `sqlalchemy` for ORM, and possibly `jsonschema` for validation. These should all run on Python 3.9+ (assumed) which is available on Raspberry Pi OS or similar. It’s recommended to use a 64-bit OS on Pi for better performance with Reticulum. Deploying the server is as simple as installing the Python package (or copying code) and ensuring the Reticulum config is in place.
* **Reticulum Configuration:** Deployment involves configuring Reticulum interfaces depending on the environment. For example, in a local testing or LAN scenario, a *TCPReticulum* interface is used (which connects to a static IP/port of another node or a hub). In field use with LoRa, the config would point to an RNode device or similar. The server must have a known identity and destination. Typically, after first run, Reticulum will create an identity (keys) in `~/.reticulum/`. We might bake in a specific destination name for the service (so that its address is derived from a known name and public key). This name and identity could be distributed to clients in advance.
* **Starting the Server:** The server can be started via a simple Python script. It could be packaged as a console script like `reticulum_openapi_server`. On startup it will:

  1. Initialize Reticulum (possibly print the destination address for logging).
  2. Initialize database (apply migrations or create tables if not exists).
  3. Instantiate controllers and register them with the service.
  4. Start the service’s message listening loop.
  5. Possibly announce its presence (Reticulum may automatically send announcements on links; we could also send an LXMF broadcast to say "API service up", but not required).
* **Resource Usage:** On a Pi or similar, this server should be able to run continuously. Memory usage likely in the tens of MBs. CPU mostly idle until a message arrives. We should consider using something like `uvloop` (an alternative event loop that’s written in C and faster) for better performance on limited hardware, though for modest loads the default asyncio loop is fine.
* **Running as a Service:** For real deployment, one would run this server as a background service (systemd on Linux, etc.). We should ensure the program handles signals to shut down gracefully. A systemd unit file can be provided to auto-start on boot, making a Pi node come online as an API endpoint whenever powered on.

### Testing Strategy

Given the critical nature (possibly used in emergency/off-grid scenarios), thorough testing is needed:

**1. Unit Testing (Offline):** Each component can be tested in isolation by simulating inputs:

* *Model Tests:* Validate that dataclasses serialize/deserialize correctly, and that JSON schema validation catches bad data. Also test ORM models if there’s business logic in them (though mostly they are definitions).
* *Controller Tests:* Since controllers are just Python logic, we can call them directly in tests. For example, create an in-memory SQLite database for test, instantiate a controller with a session to that DB, and call `await controller.add_node(test_request)`. Check that the response is correct and that the DB side effects occurred. Controllers should be tested for both normal and error flows (e.g., try to add a node that violates a constraint to see if it raises proper error).
* *Service Layer Tests:* We can simulate the service’s behavior by feeding it a fake LXMF message object. For unit tests, we might not use real Reticulum at all: instead, craft a dummy message with certain Fields and Content and call the internal routing function. This way we test that the service correctly parses, calls the controller, and forms a response. These tests can use stub controllers (a fake controller that just records that it was called or returns a known value) to isolate the routing logic.

**2. Integration Testing (Local Multinode):** For integration tests, set up a small Reticulum network in a controlled environment. The simplest is running the server and client on the same machine using the *TCP interface* to emulate two nodes:

* Start a Reticulum daemon or let the server run Reticulum in-process. Configure a TCP interface on 127.0.0.1 (say server listens on port X, client connects to port X). This makes the server and client think they are two nodes connected by a TCP link (virtually immediate communication).
* Launch the server in a background thread or subprocess from the test.
* Use the actual client code to send a request, and observe the response. For example, in a pytest, spawn the server (perhaps with an in-memory SQLite for isolation), then in the test function run `await client.send_request("add_node", sample_request)` and verify the result.
* This integration test ensures the end-to-end path (serialization, network transmission, deserialization) works. It’s essentially a full-stack test but can be run on a single machine. The Reticulum network stack is required for this; one could also monkeypatch the RNS transport to a loopback for faster tests if needed.

**3. Simulation of Network Conditions:** If possible, test how the system behaves under delay or drop conditions:

* Reticulum/LXMF can be tested by introducing an artificial propagation node or delay. For instance, use the LXMF Propagation Node mode (lxmd) to store messages for a bit, or simply simulate by not immediately delivering messages in the test harness.
* Verify that timeouts trigger on the client and that retries (if we implement any at this level) work or that the system recovers when connectivity is restored.

**4. Edge Case Testing:**

* Large payloads: Ensure that if Content is large (near LXMF limits), the system can handle it (this might involve fragmentation at Reticulum level).
* Invalid messages: Send malformed JSON or incorrect schema data from a test client and confirm the server sends a validation error.
* Concurrent messages: Fire multiple requests in parallel and see that they all get processed and each gets the correct response (no cross-talk or state bleed between handlers).

**5. Security Testing:**

* Since Reticulum provides E2E encryption, testing should verify that unauthorized nodes cannot inject commands. In practice, if they don’t have the destination address (or if the destination is set to require specific allowed senders), messages might be ignored. Our framework could optionally enforce that only known identities can call certain commands, but that’s an application layer concern. Basic security is handled by cryptography under the hood (signature verification).
* We might also test that a compromised client cannot, for example, cause an injection by sending fields that break our routing (like extremely long command name, etc.). The service should have limits and sanity checks (e.g., reject commands that are not simple alphanumeric strings or that exceed a length).

### Logging and Monitoring

For deployment, the server should include logging of events:

* Logging when a message is received (with maybe the command name and sender identity).
* Logging errors/exceptions in controllers with stack traces.
* Possibly logging when a response is sent and how long the operation took (to monitor performance).

On a Raspberry Pi, logs can go to stdout (and then captured by systemd or to a file). This helps in debugging issues in the field. Because networking might be intermittent, having a local log is important for post-mortem analysis.

### Extensibility of Deployment

While not needed initially, we design deployment such that:

* Additional service interfaces (like an HTTP server thread) can be added and started alongside the LXMF service. For example, one could run an HTTP server on the Pi for local REST calls that internally call the same controllers. Our architecture would allow that without interfering with the LXMF operation (just two different entry points into controllers).
* Plugins (mentioned later) could be deployed by dropping in additional Python modules and restarting the service. The service could be made to auto-discover controllers in certain packages, making extending the API easier. In deployment terms, this means updating the software without changing the core, only adding new files.

### Example Deployment Scenario

Imagine deploying a network of 3 Raspberry Pis in a remote area, each running this OpenAPI service and Reticulum over LoRa:

* Each Pi has the service installed and configured with LoRa interface. They might all run the same set of controllers (maybe for sensor and status commands).
* Clients (could be laptops or mobile devices with Reticulum) can send API commands like `GetSensorData` addressed to any of the Pi’s destinations. The requests propagate over the mesh (Reticulum will route via intermediate nodes if needed). The target Pi’s service picks it up, processes, and replies.
* If one Pi also has internet, in future an HTTP gateway plugin could forward API calls from a web client to LXMF and vice versa, bridging the mesh and internet.
* During deployment, one must ensure each node’s identity and address is known to the operators (maybe QR codes with their addresses). The system is flexible to accommodate this.

### Continuous Integration

Finally, from a development perspective, set up CI to run unit and integration tests, perhaps using a virtual network or just local. This ensures that any changes to schemas or controllers do not break compatibility. Because the project involves code generation (from schemas), include tests for the generation process too (e.g., generate classes and verify that they match expected field names/types).

By planning deployment and testing early, we ensure the Reticulum OpenAPI framework will be robust in the field and maintainable in development. The result is a reliable edge-service that can be easily started, scaled, and verified.

## Future Extensibility and Modular Growth

One of the design goals is to ensure that this framework can evolve. The initial implementation focuses on core messaging functionality over LXMF with a command-style API, but future expansions are anticipated. This section describes how the architecture allows extensibility and lists some possible future features or plugins that could be incorporated.

### Multi-Transport Support (Alternate Service Interfaces)

Thanks to the clean separation of the **Service** layer, we can introduce new transports/interfaces without disturbing the controllers or models. For example:

* **HTTP/REST Interface:** We could add an HTTP server (using FastAPI or Quart for async compatibility) that runs in parallel with the LXMF service. This HTTP server would expose REST endpoints corresponding to the same commands. In practice, it would receive an HTTP request, translate it to a call to the controller (perhaps even reuse the dataclass by parsing JSON body into the request dataclass), then get the response and send it back as HTTP JSON. The controllers wouldn’t know the difference – whether the call came from LXMF or HTTP. This is feasible because our controllers are just Python methods. By leveraging the same data models and validation, we ensure consistency between the mesh API and a potential REST API. This kind of dual-interface could be useful: e.g., when a device is directly connected, use HTTP for low-latency access; when remote/offline, use LXMF over mesh.
* **MQTT or Other Messaging Bridges:** Another service extension could be an MQTT bridge that subscribes to certain topics and when a message arrives, calls a controller, or vice versa. For example, bridging an “alert” command to an MQTT topic for integration with IoT platforms. The plugin would behave similarly to the LXMF service: listen for MQTT messages in an async loop, map them to controllers.
* **CLI or Local Socket:** For debugging or local control, a simple CLI interface (or a Unix domain socket accepting commands) could be added. This would allow an operator to issue commands to the server via a shell or admin tool by invoking controller methods directly. Since controllers are just Python, this is straightforward to implement as a plugin.

The architecture could formalize this by defining an abstract base class or interface for Service plugins. For example, a `BaseServiceInterface` with a method like `start()` and some way to register routes. The LXMF service and an HTTP service would both implement this. The application on startup could instantiate all configured interfaces (maybe reading a config file to decide which to enable).

### Plugin Architecture for Controllers/Modules

As the project grows, it might be useful to allow new controllers to be added as plugins. This could be done in a few ways:

* **Dynamic Discovery:** The service at startup could scan a plugins directory or check entry points (if packaged) for classes that subclass a `Controller` base class. It would auto-instantiate them and register their handlers. This way, adding a new feature is as simple as dropping a file in the directory (plus the schema for its models).
* **Modular Loading:** If the project is organized into modules (like NestJS modules concept), each module might register its controllers. We could allow enabling/disabling modules via config. For example, a “DiagnosticsModule” might include a controller for health checks. If not needed, one could disable it.
* **Third-Party Extensions:** Perhaps other developers might write controllers that integrate with this framework (for example, a controller that interfaces with a specific sensor or external API). A plugin system (with proper documentation of how to tie into the service layer) would encourage community contributions without altering core code.

### Schema Evolution and Versioning

Future changes to the API schemas should be manageable:

* We can introduce version numbers either per-command or as a whole. If a breaking change is needed, one approach is to use a new command name or a versioned namespace (e.g., `sensor.get.v2` versus `sensor.get`). The service can route accordingly, and we can keep old controllers for backward compatibility if needed.
* Because models are auto-generated, updating a schema and regenerating is straightforward. Both client and server need to update in lockstep for breaking changes, but minor, backward-compatible additions (like adding an optional field) can be handled gracefully (older clients would ignore unknown new fields, for instance).
* The framework might incorporate a version negotiation or advertising mechanism in the future (for example, a client can query the server’s version or supported commands).

### Performance Improvements

As usage scales, we might consider:

* **Caching:** Implementing caching at the service layer for certain requests. E.g., if `GetNodeStatus` is called frequently, the controller could cache results for a short time to avoid hitting a slow sensor each time. This can be done within the controller or via an added caching layer.
* **Bulk Operations:** Defining new commands that handle bulk data to reduce overhead. The architecture supports this as just another command, but it’s a design consideration at the API level.
* **Parallel Processing:** On multi-core devices, Python’s GIL limits one process’s CPU-bound concurrency. If we needed to utilize multiple cores, we could run multiple processes of the server (each with perhaps a portion of the commands or behind a load-balancer approach). Reticulum doesn’t natively load-balance (since a given destination hash is served by one instance), but one could assign different tasks to different nodes or use threading carefully for CPU tasks. Alternatively, critical sections could be moved to native code or use Python’s multiprocessing for heavy tasks.

### Additional Services via Reticulum

Reticulum itself has other capabilities (like real-time links, streams, etc.). Future extensibility might include:

* **Live Streams or LXMF Attachment handling:** Suppose in future we want to support a file transfer or streaming data as part of the API. Reticulum supports an LXMF packet containing an arbitrary payload or using additional protocols (like LXMF attachments or the LXMF “content destination” concept under development). We could extend the Service layer to handle a command that initiates a file transfer via RNS (perhaps using rncp or similar behind the scenes).
* **Event Subscription:** We could design a publish/subscribe mechanism on top of this. For example, a client might subscribe to a certain type of events (say, node status changes) and the server would push messages. Our current design is mostly request/response, but nothing prevents a controller or background task from sending an unsolicited LXMF message to a known client destination. The framework could later incorporate an **EventService** that controllers can use to emit notifications (where clients could register their address to receive those). This would be a significant extension but aligned with a real-time data need.

### Documentation and OpenAPI Integration

The name *OpenAPI* suggests we might also integrate with the OpenAPI (Swagger) specification in the future. Perhaps:

* Generate an OpenAPI (OAS3) document for the HTTP interface of this API. We could repurpose the JSON schemas to an OpenAPI spec, allowing the same API to be documented for HTTP use.
* Provide documentation for the mesh API in similar format (even if not HTTP, we can still document it like an API reference).
* The framework could include a command to output the current API schema (combining all JSON schemas) for reference or for clients to auto-configure.

### Example of Adding an HTTP Interface (Future Scenario)

To illustrate how smoothly an extension can fit, consider adding an HTTP service in a future version:

* We create a new class `HTTPService` that listens on a TCP port. Using FastAPI, we define endpoints for each command, e.g., `@app.post("/nodes/add")` calls an async function that internally does `response = await node_controller.add_node(request)` and returns `response` (FastAPI would handle serializing the dataclass to JSON automatically).
* We launch `HTTPService.start()` alongside `LXMFService.start()`. Both run on the same event loop if possible. (FastAPI with Uvicorn can run on asyncio with an API, or we integrate via Hypercorn which supports asyncio).
* We ensure thread-safety: the controllers might be called from two sources now (LXMF task or HTTP request). But since all calls are on the same async loop, they won’t truly run at the exact same time; they interleave. As long as controllers aren’t maintaining global state without locks, this is fine. If needed, one could add locks around shared resources, but typically each request is independent except the database (where transactions already isolate changes).
* The result: clients on the internet could use a REST call, and off-grid clients use LXMF, and both end up exercising the same core logic. This improves reach of the system.

### Summary of Extensibility

The framework is built with change in mind:

* New **controllers** (and thus new commands) can be added easily by writing a dataclass schema and the handler method. The registration system makes plugging it in straightforward.
* New **service interfaces** (transports) can be integrated due to the decoupled nature of the Service layer. This means the project can grow from a niche mesh API to a more universal API that spans multiple network types.
* The code structure (MCS) promotes adding features in one part without ripple effects (e.g., touching the model doesn’t usually require changing controllers except where used, adding a service doesn’t affect models, etc.).
* **Community contributions** are enabled by clear separation: one could imagine open-sourcing this and having others create modules for it (like a WeatherController that returns forecast from a sensor, etc.) which can be included as needed.

In conclusion, the Reticulum OpenAPI Python framework is not only suited for the initial edge device command handling but is **architected to evolve**. Its modular design and async foundation allow it to accommodate future requirements such as alternate communication methods, new features, and scaling enhancements, all while maintaining a clear structure and robust core. The result is a future-proof solution that can adapt alongside the Reticulum ecosystem and user needs over time.
