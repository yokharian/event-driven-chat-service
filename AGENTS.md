# AGENTS.md - Project Constitution

> I am the Law (Tech Stack & Rules). **Never ignore me.**

## 🏗️ Tech Stack

- **Backend**: AWS Lambda + API Gateway (REST + WebSocket)
- **REST API**: `APIGatewayRestResolver` (not FastAPI)
- **Database**: DynamoDB with Streams
- **Data Access**: DAL pattern with `IRepository` interface
- **Observability**: AWS Lambda Powertools
- **Frontend**: Streamlit
- **Local Development**: Docker Compose + LocalStack + SAM CLI

## 📏 Coding Standards

1. **Type Hints** — Use Python typing and Pydantic for validation
2. **Configuration** — Use `pydantic-settings` (not `os.getenv`)
3. **Lambda Handlers** — **Synchronous only** (required by `APIGatewayRestResolver`)
4. **Pydantic v2** — For all request/response models and event payloads
5. **TDD** — Test Driven Development
6. **Task Automation** — Use `poethepoet` (poe) for ALL scripts and dev commands in `pyproject.toml`**

## ✅ Required Patterns

1. **Service Layer** — Business logic in `BaseService` classes
2. **DAL Pattern** — All database operations via `IRepository` interface
3. **Dependency Injection** — Services accept repositories via constructor
4. **Powertools Decorators** — `@logger.inject_lambda_context`, `@metrics.log_metrics`, `@tracer.capture_lambda_handler`
5. **Request/Response Validation** — Pydantic models with `BaseSchema` (camelCase aliases)

## 🚫 Forbidden Patterns

1. **No Async Lambda Handlers** — Must be synchronous
2. **No Direct Database Access** — Always use repository pattern (no boto3 in services)
3. **No FastAPI** — Use `APIGatewayRestResolver` only
4. **No Hardcoded Credentials** — Use environment variables
5. **No Secrets in Repo** — Use environment variables for API keys
6. **No Makefile/Shell Scripts** — All dev commands must use `poethepoet` in `pyproject.toml`

## 🔒 Security

- **LocalStack**: `AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`
- **API Keys**: Use environment variables (e.g., `OPENAI_API_KEY`)

*This constitution is non-negotiable. All code must comply.*
