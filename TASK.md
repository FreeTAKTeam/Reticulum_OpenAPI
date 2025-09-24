# TASKS

## 2025-08-11
- [x] Fix flake8 errors across the codebase.
- [x] Add Filmology example service and client with auth tokens and schema validation.
- [x] Replace JSON serialization with MessagePack across service and tests.

- [x] Decode command responses into dataclasses in EmergencyManagement client.
- [x] Implement MessagePack decoding in EmergencyManagement client.
- [x] Add loopback link tests for client requests and resource transfer.
- [x] Update generator docs to use Python tooling and note post-generation tweaks.
- [x] Add integer range checks for MessagePack encoding.

- [x] Extend MessagePack codec tests for misordered maps, boundary vectors, digests, and negative NaN/ext cases.

- [x] Update codec Msgpack test to import from reticulum_openapi.
- [x] Introduce MessagePack utilities and refactor service/client to use them by default.
- [x] Evaluate separating compression from JSON serialization helpers.
- [x] Introduce centralised logging configuration for services and clients.

- [x] Use MessagePack for dataclass serialization and drop zlib compression.
- [x] Rename serialization helpers to dataclass_to_msgpack/from_msgpack for clarity.
- [x] Resolve merge artifacts in service tests.


## 2025-08-12
- [x] Resolve flake8 errors in services, models, and tests.


## 2025-09-16
- [x] Align LXMF client path discovery with configurable timeouts and cover success/timeout cases in tests.
- [x] Normalise LXMF command titles to handle byte-encoded message routes.
- [x] Evaluate EmergencyManagement example to resolve import issues and extend automated coverage.



## 2025-09-17
- [x] Persist and reuse Reticulum identities for services and clients when available in configuration.
- [x] Handle dataclass auth tokens in LXMF service delivery callback and extend tests.
- [x] Convert LXMF handler responses with nested dataclasses before encoding.


## 2025-09-18
- [x] Refresh EmergencyManagement README with current client/service/controller flow terminology.


## 2025-09-19
- [x] Normalise LXMF iterable handler responses to MessagePack-safe format.
- [x] Harden LXMF iterable normalisation error handling for response serialization.


## 2025-09-23
- [x] Scaffold EmergencyManagement Vite web UI with sidebar, routing, and FastAPI gateway integration.
- [x] Allow the EmergencyManagement client to reuse a stored server identity hash before prompting users.
- [x] Keep the EmergencyManagement example service running until interrupted and fix LXMF response serialisation regression.
- [x] Print EmergencyManagement client timeout message instead of exiting.
- [x] Ensure EmergencyManagement server and client announce their identities on the network.
- [x] Handle EmergencyManagement client timeouts gracefully to avoid shutdowns.
- [x] Stream LXMF announces in EmergencyManagement client using LXMFClient. (2025-09-23)

- [x] Refactor EmergencyManagement client to use shared helper library for API interactions. (2025-09-24)
- [x] Add FastAPI web gateway and API tests for EmergencyManagement example. (2025-09-23)
- [x] Build Emergency Action Messages web UI with CRUD flows, optimistic toasts, and
  Vitest coverage. (2025-09-23)
- [x] Extend Emergency Management web UI with React Query, SSE updates, and CRUD
  coverage for messages/events with automated Vitest suites.
- [x] Ensure EmergencyManagement server announces its identity using the Reticulum Destination API. (2025-09-25)
- [x] Add DestinationAnnouncer helper for LXMF services to broadcast identities.
- [x] Expose gateway status endpoint for the Emergency Management web UI. (2025-09-23)

## 2025-09-24
- [x] Restore EmergencyManagement gateway CORS defaults for web UI connectivity.
- [x] Add datetime pickers and access dropdown to the EmergencyManagement event form.
- [x] Update EmergencyManagement live updates fallback to `/notifications/stream` and align documentation/tests.
- [x] Align EmergencyManagement event detail flows with structured emergency action messages in the web UI and gateway. (2025-09-24)
- [x] Stream EmergencyService notifications to FastAPI subscribers via SSE.

