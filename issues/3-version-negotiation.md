# Feature Request: API Version Negotiation

The framework design anticipates handling schema evolution and supporting clients querying the server version or supported commands.
```
Future changes to the API schemas should be manageable:

* We can introduce version numbers either per-command or as a whole. If a breaking change is needed, one approach is to use a new command name or a versioned namespace (e.g., `sensor.get.v2` versus `sensor.get`). The service can route accordingly, and we can keep old controllers for backward compatibility if needed.
* Because models are auto-generated, updating a schema and regenerating is straightforward. Both client and server need to update in lockstep for breaking changes, but minor, backward-compatible additions (like adding an optional field) can be handled gracefully (older clients would ignore unknown new fields, for instance).
* The framework might incorporate a version negotiation or advertising mechanism in the future (for example, a client can query the server’s version or supported commands).
```

Adding a simple version negotiation mechanism would help clients remain compatible as the API changes.
