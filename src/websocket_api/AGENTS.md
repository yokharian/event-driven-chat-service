WebSocket API (LLM brief)
=========================

What it is
----------

- API Gateway WebSocket stack with three Lambda handlers: `onconnect`, `ondisconnect`, `sendmessage`.
- Local dev alternative: `local_server.py` (FastAPI) emulates API Gateway WebSocket behavior.
- Uses shared `commons` package (DAL, schemas, errors, logging helpers).

Core terms
----------

- **ConnectionId**: API Gateway ID per socket; stored in DynamoDB to target/broadcast.
- **DAL**: Repository pattern via `DynamoDBRepository`; keeps business logic DB-agnostic.
- **Broadcast**: `sendmessage` iterates stored connectionIds and sends payloads via API Gateway management API or local
  server.
- **LocalStack**: Optional DynamoDB endpoint; WebSocket API itself needs LocalStack Pro, so `local_server.py` is used
  instead.

Key files
---------

- `onconnect/app.py`: saves `connectionId` to DynamoDB on connect.
- `ondisconnect/app.py`: removes `connectionId` on disconnect.
- `sendmessage/app.py`: reads message, uses DAL, broadcasts to all active connections.
- `settings.py`: shared environment-driven configuration (table name, region, endpoints).
- `local_server.py`: local FastAPI WebSocket gateway (`ws://localhost:8080/ws` by default).

Config essentials
-----------------

- Env: `TABLE_NAME` (required), `AWS_REGION` (default `us-east-1`), `DYNAMODB_ENDPOINT_URL` (for LocalStack/dev).
- Local server extras: `WS_PORT` (default 8080).

How to run (dev)
----------------

- With LocalStack DynamoDB only:
  `export TABLE_NAME=...; export DYNAMODB_ENDPOINT_URL=http://localhost:4566; python -m src.websocket_api.local_server`
- Connect test client to `ws://localhost:8080/ws`.
