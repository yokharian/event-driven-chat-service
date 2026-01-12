Commons Package (LLM Brief)
===========================

Role
----

- Shared building blocks: DAL, schemas, enums, HTTP responses/errors, DynamoDB/PostgreSQL helpers, CORS utilities.
- Patterns: type hints + Pydantic v2 models; config via `pydantic-settings`; no direct DB access from services.

Data Access Layer (DAL)
-----------------------

- `IRepository` contract isolates business logic from storage.
- Default DynamoDB repo; PostgreSQL repo available; swap via dependency injection.

Key Modules
-----------

- `commons/dal/`: `interface.py`, `dynamodb_repository.py`, `query_builder.py`, utils for DynamoDB/PostgreSQL.
- `commons/dynamodb/`: retry/error helpers, attribute marshalling.
- `commons/responses.py` & `commons/http_errors.py`: standardized API responses/error types.
- `commons/schemas.py`: base schemas with camelCase aliases.
- `commons/cors.py`: CORS headers for API Gateway.

Usage Cues
----------

- Services receive a repository instance (DI) and call interface methods only.
- Configure endpoints/regions via env vars consumed by settings classes.
