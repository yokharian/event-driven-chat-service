## 🏗️ Tech Stack

- **Language**: Python 3.12+ (Strongly Typed)
- **Framework**: AWS Lambda Powertools (APIGatewayRestResolver)
- **Compute**: AWS Lambda (Serverless)
- **Infrastructure**: AWS API Gateway (REST + WebSocket) + DynamoDB + DynamoDB Streams
- **Infrastructure as Code**: AWS SAM / CloudFormation
- **Database**: AWS DynamoDB (via Data Access Layer pattern)
- **Code Formatter**: Black (line-length=100, target-version=py312)
- **Dependency Management**: uv (pyproject.toml + uv.lock only - **NO requirements.txt**)

---

## 📏 Coding Standards

### Backend-Specific Rules

1. **Dependency Management** — **ONLY** use `pyproject.toml` and `uv.lock` for dependencies. **NEVER** use
   `requirements.txt`. Always run `uv lock` locally to generate/update `uv.lock` before committing.
2. **API Gateway Pattern** — Use `APIGatewayRestResolver` from `aws_lambda_powertools` for REST API endpoints.
3. **Service Layer Pattern** — All business logic must be in service classes (in `services/` directory) that inherit
   from `BaseService`. Services use dependency injection for repositories, following the DAL pattern.
4. **Data Access Layer (DAL)** — Use the DAL pattern from `commons/dal/` for database operations. Services default
   to `DynamoDBRepository` but can accept any `IRepository` implementation for testing or migration.
5. **Code Formatting** — Use Black as the primary formatter. Run `poe format` to format code, `poe format-check` for CI.
   Black is configured with `line-length=100` and `target-version=py312`.
6. **Pydantic Schemas** — All request/response models must be defined in `schemas.py` using Pydantic v2 with
   `BaseSchema` (which includes camelCase aliases).
7. **Settings Management** — Use `pydantic-settings` for configuration. Settings are defined in `settings.py` and
   loaded from environment variables.

### Architecture Pattern

- **REST API**: Lambda function behind API Gateway REST API using `APIGatewayRestResolver`
- **WebSocket API**: Separate Lambda functions for `$connect`, `$disconnect`, and `sendmessage` routes (see
  `simple-websockets-chat-app-1.0.4/`)
- **Event Bus**: DynamoDB Streams trigger downstream Lambda workers (agent and delivery workers)
- **Service Layer**: Business logic in service classes, following the pattern from `engine_management/services/`
- **Repository Pattern**: Services use `BaseService` which provides dependency injection for repositories

### Event Flow Pattern

- **REST Message**: Client sends message via REST API -> Lambda writes to `chat_events` DynamoDB table
- **DynamoDB Stream**: Stream captures INSERT event with `NEW_AND_OLD_IMAGES` view
- **Agent Worker (Lambda)**: Triggered by stream -> processes user messages -> generates AI response -> writes back to
  table
- **Delivery Worker (Lambda)**: Triggered by stream -> queries active connections -> broadcasts via API Gateway
  Management API

### WebSocket Connection Management

- **OnConnect Lambda**: Validates JWT, stores connection metadata in `connections` DynamoDB table
- **OnDisconnect Lambda**: Removes connection record from DynamoDB
- **SendMessage Lambda**: Handles WebSocket messages, writes to `chat_events` table
- **Delivery Worker**: Queries `connections` table by `channel_id`, uses API Gateway Management API to send messages

---

## 🚫 Forbidden Patterns

1. **No FastAPI** — Do not use FastAPI. Use `APIGatewayRestResolver` from Lambda Powertools.
2. **No Direct DynamoDB Access** — Always use the DAL pattern through `BaseService` and repository injection.
3. **No Manual DynamoDB Item Parsing** — Use repository methods that return dictionaries, validated by Pydantic schemas.
4. **No Boto3 Resource Creation** — You cannot create AWS resources using Boto3; all resources must be defined and
   created using CloudFormation/SAM templates.
5. **No Async in Lambda Handlers** — `APIGatewayRestResolver` uses synchronous handlers. Do not use `async/await` in
   route handlers (services can use async internally if needed, but handlers are sync).

---

## ✅ Required Patterns

1. **Service Pattern** — All endpoints must instantiate a service class and call it. Do not put business logic directly
   in route handlers.
2. **Repository Injection** — Services should accept optional repository parameter for testing/migration.
3. **Error Handling** — Implement proper exception handling in services. Use `ObjectNotFoundError` from
   `commons.dynamodb.exceptions` for not found cases.
4. **Testing** — See `tests/agents.md` for testing guidelines.
5. **IaC First**: All AWS resources (API Gateway, Lambda, DynamoDB, IAM Roles) must be defined and deployed via
   **SAM/CloudFormation** templates.
6. **CloudFormation Mandatory**: Resource creation is strictly limited to CloudFormation/SAM. Boto3 is only permitted
   for
   interacting with resources (e.g., DynamoDB operations through DAL, API Gateway Management API) or deploying stacks.
7. **Powertools Integration** — Use `@metrics.log_metrics`, `@log.inject_lambda_context`, and
   `@tracer.capture_lambda_handler`
   decorators on the handler function.

---

## 📁 Project Structure

```
src/rest_api/
├── services/            # Business logic service classes
│   └── base.py         # BaseService with repository injection
└── workers/             # Lambda functions
```
