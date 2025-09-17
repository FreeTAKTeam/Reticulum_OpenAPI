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


