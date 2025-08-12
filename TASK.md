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
- [x] Use MessagePack for dataclass serialization and drop zlib compression.
- [x] Rename serialization helpers to dataclass_to_msgpack/from_msgpack for clarity.
- [x] Resolve merge artifacts in service tests.


