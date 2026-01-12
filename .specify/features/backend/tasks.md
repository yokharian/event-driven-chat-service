# Backend Tasks (src/rest_api)

## Relevant Files

- `src/infra/template-dev.yaml` - CloudFormation for API Gateway (REST+WS), DynamoDB tables/streams, IAM, Lambdas.
- `src/infra/init_infrastructure.py` - Deploys the stack to LocalStack.
- `src/rest_api/handlers/` - REST handlers using APIGatewayRestResolver.
- `src/rest_api/services/` - Business logic services (via BaseService + repositories).
- `src/rest_api/workers/agent_worker.py` - DynamoDB Streams consumer that generates AI responses.
- `src/rest_api/workers/delivery_worker.py` - DynamoDB Streams consumer that broadcasts via API Gateway Mgmt API.
- `src/rest_api/schemas.py` - Domain and pydantic models.
- `tests/backend/test_api.py` - REST/WebSocket tests.
- `tests/backend/test_messaging.py` - Messaging flow tests.
- `tests/backend/test_workers.py` - Worker flow tests.

### Notes

- All AWS resources MUST be defined in `src/infra/template-dev.yaml`; no boto3 resource creation.
- Use APIGatewayRestResolver (no FastAPI); handlers are sync.
- WebSocket is receive-only: messages are sent via REST, persisted to DynamoDB; Streams trigger workers; delivery uses
  API Gateway v2 Mgmt API.
- messaging fan-out is DynamoDB Streams + Delivery worker.
- Use `pydantic` v2 and `pydantic-settings`; config via env vars only.
- Run tests with `pytest` (backend) and `poe` tasks where available.

## Tasks

- [x] 1.0 Infrastructure as Code
    - [x] 1.1 Define DynamoDB tables/streams and IAM in `src/infra/template-dev.yaml`
    - [x] 1.2 Wire API Gateway (REST + WS) to Lambda handlers
- [x] 2.0 Containerization
    - [x] 2.1 Update `docker-compose.yml` for local stack (REST + WS + DynamoDB)
- [x] 3.0 Domain Models
    - [x] 3.1 Implement/ `Message` in `models.py`
    - [x] 3.2 Implement request/response schemas in `schemas.py` (camelCase aliases)
- [x] 4.0 REST API
    - [x] 4.2 Implement `/messages` create + list (and channel variants)
    - [x] 4.3 Implement `/internal/broadcast` for delivery worker
    - [x] 4.4 Enforce REST-only send; WS receive-only
- [x] 5.0 Workers
    - [x] 5.1 Agent worker: process stream, generate AI response, persist
    - [x] 5.2 Delivery worker: process stream, fetch connections, push via API GW Mgmt API
- [x] 6.0 Integration & Testing
    - [x] 6.1 Refactor `tests/backend/test_api.py` to DynamoDB Streams.
    - [x] 6.2 Refactor `tests/backend/test_messaging.py` to DynamoDB Streams.
    - [x] 6.3 Refactor `tests/backend/test_workers.py` to DynamoDB Streams.
    - [ ] 6.4 End-to-end local: REST send -> stream -> agent -> delivery -> WS receive
