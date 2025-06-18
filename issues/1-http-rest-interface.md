# Feature Request: HTTP/REST Interface

The design specification outlines adding a parallel HTTP service so the same controllers can be exposed as REST endpoints. Key excerpts:
```
Thanks to the clean separation of the **Service** layer, we can introduce new transports/interfaces without disturbing the controllers or models. For example:

* **HTTP/REST Interface:** We could add an HTTP server (using FastAPI or Quart for async compatibility) that runs in parallel with the LXMF service. This HTTP server would expose REST endpoints corresponding to the same commands. In practice, it would receive an HTTP request, translate it to a call to the controller (perhaps even reuse the dataclass by parsing JSON body into the request dataclass), then get the response and send it back as HTTP JSON. The controllers wouldn’t know the difference – whether the call came from LXMF or HTTP. This is feasible because our controllers are just Python methods. By leveraging the same data models and validation, we ensure consistency between the mesh API and a potential REST API. This kind of dual-interface could be useful: e.g., when a device is directly connected, use HTTP for low-latency access; when remote/offline, use LXMF over mesh.
* **MQTT or Other Messaging Bridges:** Another service extension could be an MQTT bridge that subscribes to certain topics and when a message arrives, calls a controller, or vice versa. For example, bridging an “alert” command to an MQTT topic for integration with IoT platforms. The plugin would behave similarly to the LXMF service: listen for MQTT messages in an async loop, map them to controllers.
* **CLI or Local Socket:** For debugging or local control, a simple CLI interface (or a Unix domain socket accepting commands) could be added. This would allow an operator to issue commands to the server via a shell or admin tool by invoking controller methods directly. Since controllers are just Python, this is straightforward to implement as a plugin.

The architecture could formalize this by defining an abstract base class or interface for Service plugins. For example, a `BaseServiceInterface` with a method like `start()` and some way to register routes. The LXMF service and an HTTP service would both implement this. The application on startup could instantiate all configured interfaces (maybe reading a config file to decide which to enable).
```
```
### Example of Adding an HTTP Interface (Future Scenario)

To illustrate how smoothly an extension can fit, consider adding an HTTP service in a future version:

* We create a new class `HTTPService` that listens on a TCP port. Using FastAPI, we define endpoints for each command, e.g., `@app.post("/nodes/add")` calls an async function that internally does `response = await node_controller.add_node(request)` and returns `response` (FastAPI would handle serializing the dataclass to JSON automatically).
* We launch `HTTPService.start()` alongside `LXMFService.start()`. Both run on the same event loop if possible. (FastAPI with Uvicorn can run on asyncio with an API, or we integrate via Hypercorn which supports asyncio).
* We ensure thread-safety: the controllers might be called from two sources now (LXMF task or HTTP request). But since all calls are on the same async loop, they won’t truly run at the exact same time; they interleave. As long as controllers aren’t maintaining global state without locks, this is fine. If needed, one could add locks around shared resources, but typically each request is independent except the database (where transactions already isolate changes).
* The result: clients on the internet could use a REST call, and off-grid clients use LXMF, and both end up exercising the same core logic. This improves reach of the system.
```

Implementing an `HTTPService` would allow clients to interact via HTTP when direct connectivity is available while keeping LXMF support for mesh networking.
