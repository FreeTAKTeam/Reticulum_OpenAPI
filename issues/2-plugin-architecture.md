# Feature Request: Plugin Architecture for Controllers and Services

The design spec mentions adding a plugin system to dynamically load controllers and additional service interfaces.
```
### Plugin Architecture for Controllers/Modules

As the project grows, it might be useful to allow new controllers to be added as plugins. This could be done in a few ways:

* **Dynamic Discovery:** The service at startup could scan a plugins directory or check entry points (if packaged) for classes that subclass a `Controller` base class. It would auto-instantiate them and register their handlers. This way, adding a new feature is as simple as dropping a file in the directory (plus the schema for its models).
* **Modular Loading:** If the project is organized into modules (like NestJS modules concept), each module might register its controllers. We could allow enabling/disabling modules via config. For example, a “DiagnosticsModule” might include a controller for health checks. If not needed, one could disable it.
* **Third-Party Extensions:** Perhaps other developers might write controllers that integrate with this framework (for example, a controller that interfaces with a specific sensor or external API). A plugin system (with proper documentation of how to tie into the service layer) would encourage community contributions without altering core code.
```

Implementing this would let developers drop in new functionality without modifying the core codebase.
