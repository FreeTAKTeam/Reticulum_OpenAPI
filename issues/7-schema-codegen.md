# Feature Request: Schema-Based Dataclass Generation

The model layer description suggests auto-generating dataclasses from JSON Schema or OpenAPI definitions.
```

Models define the data structures and persistence logic of the application. In this framework, models have two parts:

* **Data Transfer Models:** Python dataclasses generated from JSON Schema or OpenAPI definitions represent the structure of API messages. Each dataclass corresponds to a request or response schema for a particular command/endpoint. These are lightweight plain dataclasses (or Pydantic models, if validation is needed) that enforce types and facilitate JSON (de)serialization. By auto-generating them from schemas, we ensure **schema-based validation** — incoming JSON content can be validated against the schema and parsed into a dataclass, guaranteeing it conforms to the expected format.
* **ORM Persistence Models:** For any persistent data (e.g. configuration, user records, sensor readings), the framework uses SQLAlchemy ORM models. These are classes mapped to database tables (SQLite or other SQL databases) that allow storing and querying data. The ORM models encapsulate how data is saved or retrieved, whereas the dataclass models encapsulate the in-message representation. In many cases, the structure of a dataclass will mirror an ORM model for convenience, but they serve different purposes (one for messaging, one for storage).

**Key responsibilities of the Model layer:**

* Define **dataclass schemas** for all API message types (requests and responses). This can be automated by a code generator that reads JSON schema files and produces `@dataclass` classes with appropriate fields and types. These dataclasses may include basic validation (via type hints or Pydantic if used) to ensure data integrity.
* Perform **validation of incoming data** against the JSON schema. The framework should integrate a JSON Schema validation step (using a library like `jsonschema`) or rely on dataclass/Pydantic validation to reject malformed messages. This guarantees the server only processes commands with expected fields and types, as defined in the protocol spec.
```

A code generator would keep client and server models in sync and ensure validation against the schema.
