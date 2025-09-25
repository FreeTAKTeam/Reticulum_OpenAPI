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
- [x] Ensure EmergencyManagement client runs until interrupted.
- [x] Surface dashboard gateway errors using extractApiErrorMessage and recover view state after successful loads.
- [x] Surface gateway server identity and API configuration details on the dashboard page.

## 2025-09-25
- [x] Document how to start the Emergency Management FastAPI gateway on http://localhost:8000 in the project README.
- [x] Add random event seeding helper for the EmergencyManagement client CLI.
- [x] Ensure EmergencyManagement FastAPI gateway decodes compressed responses when relaying server commands.
- [x] Refresh EmergencyManagement web UI with dark styling and navigation/status icons inspired by mission dashboard designs.
- [x] Enable LXMF service link support and extend automated coverage.
- [x] Ensure EmergencyManagement gateway retries LXMF link until connection established. (2025-09-30)
- [x] Add HTTP integration tests for the EmergencyManagement web UI message and event flows.
- [x] Surface active Reticulum interfaces in the EmergencyManagement gateway startup logs and dashboard.
- [x] Upgrade esbuild dependency to version 0.25.0 or later to address the development server request vulnerability.
- [x] Simplify EmergencyManagement web UI tables with a drawer form triggered by a New button. (2025-09-25)

